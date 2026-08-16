select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select issue_code
from "dwh"."mart"."mart_sm_quality_issues"
where issue_code is null



      
    ) dbt_internal_test