select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select validated_at
from "dwh"."mart"."mart_sm_pipeline_status"
where validated_at is null



      
    ) dbt_internal_test