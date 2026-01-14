
  create view "dwh"."staging"."stg_gh_pandas_issues__dbt_tmp"
    
    
  as (
    

with src as (
    select *
    from "dwh"."raw"."gh_pandas_issues"
)

select
    id::bigint                           as issue_id,
    number::bigint                       as issue_number,
    repository::text                     as repo_name,
    repository_url::text                 as repository_url,
    user_id::bigint                      as author_user_id,
    (user::jsonb ->> 'login')::text      as author_login,
    state::text                          as issue_state,
    state_reason::text                   as issue_state_reason,
    title::text                          as issue_title,
    body::text                           as issue_body,
    coalesce(comments, 0)::bigint        as issue_comment_count,
    created_at::timestamptz              as issue_created_at,
    updated_at::timestamptz              as issue_updated_at,
    closed_at::timestamptz               as issue_closed_at,
    html_url::text                       as issue_url,
    _airbyte_extracted_at::timestamptz   as _airbyte_extracted_at,
    _airbyte_raw_id::text                as _airbyte_raw_id
from src
  );