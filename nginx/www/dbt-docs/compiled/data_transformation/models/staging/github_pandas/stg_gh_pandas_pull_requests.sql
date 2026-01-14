

with src as (
    select *
    from "dwh"."raw"."gh_pandas_pull_requests"
)

select
    id::bigint                                      as pr_id,
    number::bigint                                  as pr_number,
    repository::text                                as repo_name,
    (user::jsonb ->> 'login')::text                 as author_login,
    state::text                                     as pr_state,
    title::text                                     as pr_title,
    body::text                                      as pr_body,
    draft::boolean                                  as is_draft,
    created_at::timestamptz                         as pr_created_at,
    updated_at::timestamptz                         as pr_updated_at,
    closed_at::timestamptz                          as pr_closed_at,
    merged_at::timestamptz                          as pr_merged_at,
    html_url::text                                  as pr_url,
    diff_url::text                                  as diff_url,
    patch_url::text                                 as patch_url,
    issue_url::text                                 as issue_url,
    (base::jsonb -> 'repo' ->> 'full_name')::text   as base_repo_full_name,
    (base::jsonb ->> 'ref')::text                   as base_ref,
    (head::jsonb -> 'repo' ->> 'full_name')::text   as head_repo_full_name,
    (head::jsonb ->> 'ref')::text                   as head_ref,
    merge_commit_sha::text                          as merge_commit_sha,
    author_association::text                        as author_association,
    _airbyte_extracted_at::timestamptz              as _airbyte_extracted_at,
    _airbyte_raw_id::text                           as _airbyte_raw_id
from src