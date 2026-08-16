

with products as (
    select * from "dwh"."staging"."stg_sm_products"
),

margin as (
    select * from "dwh"."staging"."stg_sm_margin"
)

select
    p.product_id,
    p.product_name,
    p.product_group,
    m.margin_per_unit,
    p.has_duplicate_source_rows
from products p
left join margin m on m.product_id = p.product_id

union all

select
    '-1'                as product_id,
    'Unknown Product'   as product_name,
    'Unknown'           as product_group,
    null::numeric       as margin_per_unit,
    false               as has_duplicate_source_rows