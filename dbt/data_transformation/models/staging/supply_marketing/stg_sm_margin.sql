{{ config(schema='staging', materialized='view', tags=['supply_marketing_reporting']) }}

with src as (
    select
        trim(product_id)::text        as product_id,
        trim(margin_per_unit)::numeric as margin_per_unit,
        _source_file::text            as _source_file,
        _loaded_at::timestamp         as _loaded_at
    from {{ source('supply_marketing', 'raw_margin') }}
)

select * from src
