{{ config(schema='mart', materialized='table', tags=['supply_marketing_reporting']) }}

-- Unified data quality issue register, covering every grain the assessment identified.
--
-- mart_sm_data_quality reports one row per flagged *transaction*, so master data
-- problems had nowhere to surface: the near-duplicate customers (C007/C008) and the
-- deduplicated product key (P300) were modelled as flags on the dimensions and shown
-- nowhere. The assessment claims seven issues while the dashboard could only show the
-- transaction-level ones.
--
-- Rather than force master data rows into a transaction-grained table - which would
-- break that model's grain and its unique test - this model normalises every issue to
-- a common shape: one row per (scope, entity, issue code). That is a clean grain of its
-- own, and it lets a single card report across transactions, customers and products.
--
-- is_blocking distinguishes the rules that exclude a transaction from headline KPIs
-- from those that are reported but still counted. Master data flags are never blocking:
-- they are business questions raised for review, not grounds for dropping a number.

with transaction_issues as (
    select
        'transaction'                                   as issue_scope,
        s.transaction_id                                as entity_id,
        s.transaction_id                                as entity_label,
        code                                            as issue_code,
        code <> 'possible_duplicate_transaction'        as is_blocking,
        abs(s.gross_revenue)                            as revenue_affected
    from {{ ref('stg_sm_sales') }} s
    cross join lateral unnest(s.dq_issues) as code
),

customer_issues as (
    select
        'customer'                          as issue_scope,
        c.customer_id                       as entity_id,
        c.customer_name                     as entity_label,
        'possible_duplicate_customer'       as issue_code,
        false                               as is_blocking,
        -- No revenue is at risk: both keys are valid and every transaction against
        -- them is counted. What is uncertain is whether two rows are one company.
        null::numeric                       as revenue_affected
    from {{ ref('dim_sm_customer') }} c
    where c.is_possible_duplicate_customer
),

product_issues as (
    select
        'product'                       as issue_scope,
        p.product_id                    as entity_id,
        p.product_name                  as entity_label,
        'duplicate_source_rows'         as issue_code,
        false                           as is_blocking,
        -- Already resolved in staging by deduplication; recorded so the fix is
        -- visible rather than silent.
        null::numeric                   as revenue_affected
    from {{ ref('dim_sm_product') }} p
    where p.has_duplicate_source_rows
)

select * from transaction_issues
union all
select * from customer_issues
union all
select * from product_issues
