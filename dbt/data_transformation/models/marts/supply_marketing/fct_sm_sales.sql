{{ config(schema='mart', materialized='table', tags=['supply_marketing_reporting']) }}

-- Reporting fact table: one row per source transaction. Every source row is
-- carried forward, including rows that failed a staging data quality rule, so
-- the fact can describe its own completeness rather than silently omitting
-- records. dq_valid marks the rows fit for headline KPIs; consumers filter on
-- it explicitly and the dashboard defaults to dq_valid = true.
--
-- Keys that cannot be resolved against a dimension are routed to the '-1'
-- Unknown member so the flagged rows join cleanly and referential integrity
-- holds. The unresolved source values are retained as source_customer_id /
-- source_product_id. The relationships tests in marts.yml are what guard this.

with sales as (
    select *
    from {{ ref('stg_sm_sales') }}
),

resolved as (
    select
        s.*,

        -- Reuse the issue flags staging already computed rather than
        -- re-deriving dimension membership here.
        case
            when s.issue_missing_customer_id or s.issue_unknown_customer_id
            then '-1'
            else s.customer_id
        end                                     as customer_key,

        -- Staging has no "missing product id" rule, so a null product_id would
        -- not trip issue_unknown_product_id. Resolving null here as well keeps
        -- the key total, so the not_null test cannot be defeated by a source
        -- row the staging rules do not currently anticipate.
        case
            when s.issue_unknown_product_id or s.product_id is null
            then '-1'
            else s.product_id
        end                                     as product_key
    from sales s
),

product as (
    select product_id, margin_per_unit
    from {{ ref('dim_sm_product') }}
)

select
    s.transaction_id,
    s.transaction_date,
    s.customer_key                              as customer_id,
    s.product_key                               as product_id,
    s.customer_id                               as source_customer_id,
    s.product_id                                as source_product_id,
    s.country                                   as transaction_country,
    s.currency,

    s.quantity                                  as volume,
    s.unit_price,
    s.gross_revenue                             as revenue,
    -- The Unknown product member carries a null margin_per_unit, so orphan
    -- product rows get a null margin rather than a fabricated one.
    s.quantity * p.margin_per_unit              as margin,

    s.dq_valid,
    s.dq_issues,
    array_to_string(s.dq_issues, ', ')          as dq_issues_label,

    s.is_possible_duplicate_transaction,
    s._source_file,
    s._loaded_at
from resolved s
left join product p on p.product_id = s.product_key
