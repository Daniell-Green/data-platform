
  
    

  create  table "dwh"."mart"."mart_sm_data_quality__dbt_tmp"
  
  
    as
  
  (
    

-- Powers the Data Quality view of the dashboard. Every flagged row is listed
-- with the revenue it represents, so the business can see not just how many
-- records are affected but how much value is excluded from or at risk in the
-- reported KPIs.

with sales as (
    select * from "dwh"."staging"."stg_sm_sales"
),

totals as (
    select
        count(*)                     as total_row_count,
        sum(abs(gross_revenue))      as total_abs_revenue
    from sales
)

select
    s.transaction_id,
    s.transaction_date,
    s.customer_id,
    s.product_id,
    s.quantity,
    s.unit_price,
    s.gross_revenue,
    s.country,

    s.dq_valid,
    s.dq_issues,
    array_to_string(s.dq_issues, ', ')          as dq_issues_label,

    case when s.dq_valid then 0 else abs(s.gross_revenue) end   as revenue_excluded_from_kpis,

    t.total_row_count,
    t.total_abs_revenue,
    round(100.0 * abs(s.gross_revenue) / nullif(t.total_abs_revenue, 0), 2) as pct_of_total_abs_revenue,

    s._source_file,
    s._loaded_at
from sales s
cross join totals t
where cardinality(s.dq_issues) > 0
  );
  