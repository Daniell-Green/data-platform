select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select entity_id
from "dwh"."mart"."mart_sm_quality_issues"
where entity_id is null



      
    ) dbt_internal_test