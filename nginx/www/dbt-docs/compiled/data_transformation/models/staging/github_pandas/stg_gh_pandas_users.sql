

with src as (
    select *
    from "dwh"."raw"."gh_pandas_users"
)

select
    id::bigint                          as user_id,
    login::text                         as user_login,
    type::text                          as user_type,
    site_admin::boolean                 as is_site_admin,
    html_url::text                      as user_url,
    avatar_url::text                    as avatar_url,
    organization::text                  as organization,
    repos_url::text                     as repos_url,
    followers_url::text                 as followers_url,
    following_url::text                 as following_url,
    _airbyte_extracted_at::timestamptz  as _airbyte_extracted_at,
    _airbyte_raw_id::text               as _airbyte_raw_id
from src