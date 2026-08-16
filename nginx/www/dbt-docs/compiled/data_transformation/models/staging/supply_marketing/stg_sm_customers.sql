

-- C007 "Jet Fuels GmbH" and C008 "Jet Fuel GmbH" are near-identical names on two
-- distinct, valid customer IDs. Unlike the duplicate product key, nothing is
-- structurally broken here — both IDs join cleanly and neither fans out the fact
-- table. Whether these are one legal entity or two is a master-data question the
-- source data cannot answer (no VAT ID, no address). Merging them automatically
-- would risk misattributing revenue between two real customers, so both are kept
-- and the ambiguity is flagged for business review instead.

with src as (
    select
        trim(customer_id)::text    as customer_id,
        trim(customer_name)::text  as customer_name,
        trim(segment)::text        as segment,
        trim(country)::text        as country,
        _source_file::text         as _source_file,
        _loaded_at::timestamp      as _loaded_at
    from "dwh"."raw"."raw_customers"
),

-- Normalised name: lowercase, drop punctuation, strip the legal form, remove
-- remaining whitespace, then fold a trailing plural "s" so "Jet Fuels" and
-- "Jet Fuel" collide.
normalised as (
    select
        *,
        regexp_replace(
            regexp_replace(
                regexp_replace(lower(customer_name), '[^a-z0-9 ]', '', 'g'),
                '(^| )(gmbh|ag|se|kg|ltd|plc|bv|sa|spa)( |$)', ' ', 'g'
            ),
            '[^a-z0-9]', '', 'g'
        ) as name_key
    from src
),

folded as (
    select
        *,
        regexp_replace(name_key, 's$', '') as name_key_folded
    from normalised
)

select
    customer_id,
    customer_name,
    segment,
    country,
    count(*) over (partition by name_key_folded) > 1 as is_possible_duplicate_customer,
    _source_file,
    _loaded_at
from folded