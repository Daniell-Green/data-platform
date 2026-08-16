select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select margin_per_unit
from "dwh"."staging"."stg_sm_margin"
where margin_per_unit is null



      
    ) dbt_internal_test