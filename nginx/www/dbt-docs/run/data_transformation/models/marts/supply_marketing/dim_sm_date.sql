
  
    

  create  table "dwh"."mart"."dim_sm_date__dbt_tmp"
  
  
    as
  
  (
    

-- Generated across the span of observed transactions so revenue trends show gaps
-- as gaps rather than skipping missing days entirely.

with bounds as (
    select
        date_trunc('month', min(transaction_date))::date                          as start_date,
        (date_trunc('month', max(transaction_date)) + interval '1 month - 1 day')::date as end_date
    from "dwh"."staging"."stg_sm_sales"
    where transaction_date is not null
),

days as (
    select generate_series(start_date, end_date, interval '1 day')::date as date_day
    from bounds
)

select
    date_day,
    extract(year  from date_day)::int    as calendar_year,
    extract(month from date_day)::int    as calendar_month,
    to_char(date_day, 'YYYY-MM')         as year_month,
    to_char(date_day, 'Mon YYYY')        as year_month_label,
    extract(quarter from date_day)::int  as calendar_quarter,
    to_char(date_day, 'Day')             as day_name
from days
  );
  