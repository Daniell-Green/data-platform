select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

with all_values as (

    select
        issue_scope as value_field,
        count(*) as n_records

    from "dwh"."mart"."mart_sm_quality_issues"
    group by issue_scope

)

select *
from all_values
where value_field not in (
    'transaction','customer','product'
)



      
    ) dbt_internal_test