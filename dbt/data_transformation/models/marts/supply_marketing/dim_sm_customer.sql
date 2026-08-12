{{ config(schema='mart', materialized='table', tags=['supply_marketing_reporting']) }}

with customers as (
    select * from {{ ref('stg_sm_customers') }}
)

select
    customer_id,
    customer_name,
    segment,
    country                         as customer_country,
    is_possible_duplicate_customer
from customers

union all

-- Unknown member. Sales rows with a missing or unresolvable customer are
-- excluded from the KPI marts, but the member exists so the dimension can still
-- describe them in the data quality view without breaking joins.
select
    '-1'                as customer_id,
    'Unknown Customer'  as customer_name,
    'Unknown'           as segment,
    'Unknown'           as customer_country,
    false               as is_possible_duplicate_customer
