select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select is_blocking
from "dwh"."mart"."mart_sm_quality_issues"
where is_blocking is null



      
    ) dbt_internal_test