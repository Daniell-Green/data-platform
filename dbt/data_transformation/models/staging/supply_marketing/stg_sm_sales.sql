{{ config(schema='staging', materialized='view', tags=['supply_marketing_reporting']) }}

-- Every raw sales row is carried forward. Nothing is dropped or corrected here.
-- Rows that fail a data quality rule are marked dq_valid = false and carry the
-- reason codes in dq_issues, so they stay countable and reportable in the data
-- quality mart. Only the marts layer filters on dq_valid, and it does so
-- explicitly.

with src as (
    select
        trim(transaction_id)::text                        as transaction_id,
        to_date(trim(transaction_date), 'DD.MM.YYYY')     as transaction_date,
        nullif(trim(customer_id), '')::text               as customer_id,
        nullif(trim(product_id), '')::text                as product_id,
        trim(quantity)::numeric                           as quantity,
        trim(unit_price)::numeric                         as unit_price,
        trim(currency)::text                              as currency,
        trim(country)::text                               as country,
        _source_file::text                                as _source_file,
        _loaded_at::timestamp                             as _loaded_at
    from {{ source('supply_marketing', 'raw_sales') }}
),

known_products as (
    select product_id from {{ ref('stg_sm_products') }}
),

known_customers as (
    select customer_id from {{ ref('stg_sm_customers') }}
),

flagged as (
    select
        s.*,

        s.customer_id is null                                              as issue_missing_customer_id,
        s.product_id is not null
            and not exists (select 1 from known_products p where p.product_id = s.product_id)
                                                                           as issue_unknown_product_id,
        s.customer_id is not null
            and not exists (select 1 from known_customers c where c.customer_id = s.customer_id)
                                                                           as issue_unknown_customer_id,
        s.quantity < 0                                                     as issue_negative_quantity,

        -- Identical in every business attribute but with a distinct
        -- transaction_id. transaction_id is assumed to be assigned by the source
        -- system, so this is surfaced for review rather than treated as a
        -- duplicate: these rows remain dq_valid and stay in the KPI marts.
        count(*) over (
            partition by s.transaction_date, s.customer_id, s.product_id,
                         s.quantity, s.unit_price, s.currency, s.country
        ) > 1                                                              as is_possible_duplicate_transaction

    from src s
)

select
    transaction_id,
    transaction_date,
    customer_id,
    product_id,
    quantity,
    unit_price,
    quantity * unit_price   as gross_revenue,
    currency,
    country,

    issue_missing_customer_id,
    issue_unknown_customer_id,
    issue_unknown_product_id,
    issue_negative_quantity,
    is_possible_duplicate_transaction,

    not (
        issue_missing_customer_id
        or issue_unknown_customer_id
        or issue_unknown_product_id
        or issue_negative_quantity
    ) as dq_valid,

    array_remove(
        array[
            case when issue_missing_customer_id  then 'missing_customer_id'  end,
            case when issue_unknown_customer_id  then 'unknown_customer_id'  end,
            case when issue_unknown_product_id   then 'unknown_product_id'   end,
            case when issue_negative_quantity    then 'negative_quantity'    end,
            case when is_possible_duplicate_transaction then 'possible_duplicate_transaction' end
        ],
        null
    ) as dq_issues,

    _source_file,
    _loaded_at
from flagged
