

with repo as (
    select *
    from "dwh"."staging"."stg_gh_pandas_repositories"
),

activity_30d as (
    select
        repo_full_name,
        sum(issues_created)   as issues_created_30d,
        sum(prs_created)      as prs_created_30d,
        sum(prs_merged)       as prs_merged_30d,
        sum(comments_created) as comments_created_30d
    from "dwh"."mart"."mart_repo_daily_activity"
    where day >= (current_date - 30)
    group by 1
)

select
    r.repo_id,
    r.repo_full_name,
    r.language,
    r.stargazers_count,
    r.forks_count,
    r.open_issues_count,
    r.repo_created_at,
    r.repo_updated_at,
    coalesce(a.issues_created_30d, 0) as issues_created_30d,
    coalesce(a.prs_created_30d, 0) as prs_created_30d,
    coalesce(a.prs_merged_30d, 0) as prs_merged_30d,
    coalesce(a.comments_created_30d, 0) as comments_created_30d
from repo r
left join activity_30d a on a.repo_full_name = r.repo_full_name