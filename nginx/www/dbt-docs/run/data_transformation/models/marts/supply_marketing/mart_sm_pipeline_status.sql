
  
    

  create  table "dwh"."mart"."mart_sm_pipeline_status__dbt_tmp"
  
  
    as
  
  (
    

-- Freshness indicator for the dashboard.
--
-- The point of this model is what it does NOT do. Because the DAG runs `dbt build`
-- rather than `dbt run` followed by `dbt test`, dbt skips any model whose upstream
-- tests failed. This model depends on the fact and both dimensions, so it is only
-- rebuilt when they have actually passed validation.
--
-- validated_at therefore means "the last time the marts passed their tests", not
-- "the last time the pipeline ran". If a test fails, this table keeps its previous
-- timestamp and the dashboard card visibly goes stale, instead of the failure being
-- invisible to everyone reading the numbers.
--
-- Deliberately one row, so a BI card can read it as a scalar without aggregation.

select
    current_timestamp::timestamp without time zone      as validated_at,

    (select count(*) from "dwh"."mart"."fct_sm_sales")                    as fact_row_count,
    (select count(*) from "dwh"."mart"."fct_sm_sales" where dq_valid)     as valid_row_count,
    (select count(*) from "dwh"."mart"."fct_sm_sales" where not dq_valid) as flagged_row_count,

    -- When the source files were last landed in raw, as opposed to when the marts
    -- were last rebuilt. A large gap between the two means the pipeline is rebuilding
    -- stale source data.
    (select max(_loaded_at) from "dwh"."mart"."fct_sm_sales")             as source_loaded_at,

    (select count(*) from "dwh"."mart"."dim_sm_customer")                 as customer_count,
    (select count(*) from "dwh"."mart"."dim_sm_product")                  as product_count
  );
  