select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select dq_valid
from "dwh"."mart"."fct_sm_sales"
where dq_valid is null



      
    ) dbt_internal_test