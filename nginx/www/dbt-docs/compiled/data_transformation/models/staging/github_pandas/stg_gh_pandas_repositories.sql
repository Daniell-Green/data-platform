

with src as (
    select *
    from "dwh"."raw"."gh_pandas_repositories"
)

select
    id::bigint                                as repo_id,
    full_name::text                           as repo_full_name,
    name::text                                as repo_name,
    (owner::jsonb ->> 'login')::text          as owner_login,
    (owner::jsonb ->> 'id')::bigint           as owner_id,
    html_url::text                            as repo_url,
    language::text                            as "language",
    coalesce(stargazers_count, 0)::bigint     as stargazers_count,
    coalesce(forks_count, 0)::bigint          as forks_count,
    coalesce(open_issues_count, 0)::bigint    as open_issues_count,
    coalesce(watchers_count, 0)::bigint       as watchers_count,
    fork::boolean                             as is_fork,
    private::boolean                          as is_private,
    archived::boolean                         as is_archived,
    disabled::boolean                         as is_disabled,
    visibility::text                          as visibility,
    default_branch::text                      as default_branch,
    created_at::timestamptz                   as repo_created_at,
    updated_at::timestamptz                   as repo_updated_at,
    pushed_at::timestamptz                    as repo_pushed_at,
    description::text                         as description,
    homepage::text                            as homepage,
    _airbyte_extracted_at::timestamptz        as _airbyte_extracted_at,
    _airbyte_raw_id::text                     as _airbyte_raw_id
from src