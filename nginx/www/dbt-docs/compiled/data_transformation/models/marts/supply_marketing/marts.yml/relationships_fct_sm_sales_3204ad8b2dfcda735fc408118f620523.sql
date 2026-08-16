
    
    

with child as (
    select product_id as from_field
    from "dwh"."mart"."fct_sm_sales"
    where product_id is not null
),

parent as (
    select product_id as to_field
    from "dwh"."mart"."dim_sm_product"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


