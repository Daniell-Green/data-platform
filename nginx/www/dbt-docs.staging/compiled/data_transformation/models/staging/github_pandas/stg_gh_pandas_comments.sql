

with src as (
    select *
    from "dwh"."raw"."gh_pandas_comments"
)

select
    id::bigint                           as comment_id,
    repository::text                     as repo_name,
    user_id::bigint                      as commenter_user_id,
    (user::jsonb ->> 'login')::text      as commenter_login,
    created_at::timestamptz              as comment_created_at,
    updated_at::timestamptz              as comment_updated_at,
    html_url::text                       as comment_url,
    issue_url::text                      as issue_url,
    body::text                           as comment_body,
    author_association::text             as author_association,
    _airbyte_extracted_at::timestamptz   as _airbyte_extracted_at,
    _airbyte_raw_id::text                as _airbyte_raw_id
from src