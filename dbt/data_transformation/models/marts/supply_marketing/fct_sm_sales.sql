{{ config(schema='mart', materialized='table', tags=['supply_marketing_reporting']) }}

-- Reporting fact table: one row per source transaction, restricted to rows that
-- passed the staging data quality rules. Flagged rows are deliberately excluded
-- so headline KPIs are not distorted by data known to be unreliable; they remain
-- fully visible in mart_sm_data_quality.

with sales as (
    select *
    from {{ ref('stg_sm_sales') }}
    where dq_valid
),

product as (
    select product_id, margin_per_unit
    from {{ ref('dim_sm_product') }}
)

select
    s.transaction_id,
    s.transaction_date,
    s.customer_id,
    s.product_id,
    s.country                                   as transaction_country,
    s.currency,

    s.quantity                                  as volume,
    s.unit_price,
    s.gross_revenue                             as revenue,
    s.quantity * p.margin_per_unit              as margin,

    s.is_possible_duplicate_transaction,
    s._source_file,
    s._loaded_at
from sales s
left join product p on p.product_id = s.product_id
