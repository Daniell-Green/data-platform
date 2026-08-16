
  create view "dwh"."staging"."stg_sm_products__dbt_tmp"
    
    
  as (
    

-- Products.xlsx contains P300 twice, with two spellings of the same product
-- ("Jet A1" / "Jet A-1"). A duplicate key here is a *structural* defect, not a
-- business ambiguity: leaving it in place would fan out every P300 sale into two
-- fact rows and double-count that revenue. It is therefore deduplicated here.
--
-- Survivorship rule: keep the alphabetically-first product_name per product_id.
-- The rule is arbitrary but deterministic — the point is that the same input
-- always yields the same output. Both raw spellings remain in raw.raw_products
-- for audit, and duplicate keys are surfaced in the data quality mart.

with src as (
    select
        trim(product_id)::text     as product_id,
        trim(product_name)::text   as product_name,
        trim(product_group)::text  as product_group,
        _source_file::text         as _source_file,
        _loaded_at::timestamp      as _loaded_at
    from "dwh"."raw"."raw_products"
),

ranked as (
    select
        *,
        count(*)     over (partition by product_id)                        as source_row_count,
        row_number() over (partition by product_id order by product_name)  as survivorship_rank
    from src
)

select
    product_id,
    product_name,
    product_group,
    source_row_count > 1 as has_duplicate_source_rows,
    _source_file,
    _loaded_at
from ranked
where survivorship_rank = 1
  );