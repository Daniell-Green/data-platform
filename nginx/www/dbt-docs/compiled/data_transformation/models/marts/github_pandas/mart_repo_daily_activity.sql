

with repos as (
    select
        repo_id,
        repo_full_name
    from "dwh"."staging"."stg_gh_pandas_repositories"
),

issue_daily as (
    select
        repo_name                                   as repo_full_name,
        date_trunc('day', issue_created_at)::date   as "day",
        count(*)                                    as issues_created
    from "dwh"."staging"."stg_gh_pandas_issues"
    group by 1,2
),

pr_daily as (
    select
        repo_name                               as repo_full_name,
        date_trunc('day', pr_created_at)::date  as "day",
        count(*)                                as prs_created,
        sum(case when pr_merged_at is not null then 1 else 0 end) as prs_merged
    from "dwh"."staging"."stg_gh_pandas_pull_requests"
    group by 1,2
),

comment_daily as (
    select
        repo_name                                   as repo_full_name,
        date_trunc('day', comment_created_at)::date as "day",
        count(*)                                    as comments_created
    from "dwh"."staging"."stg_gh_pandas_comments"
    group by 1,2
),

all_days as (
    select repo_full_name, day from issue_daily
    union
    select repo_full_name, day from pr_daily
    union
    select repo_full_name, day from comment_daily
)

select
    r.repo_id,
    r.repo_full_name,
    d.day,
    coalesce(i.issues_created, 0)   as issues_created,
    coalesce(p.prs_created, 0)      as prs_created,
    coalesce(p.prs_merged, 0)       as prs_merged,
    coalesce(c.comments_created, 0) as comments_created
from all_days d
left join repos r on r.repo_full_name = d.repo_full_name
left join issue_daily i on i.repo_full_name = d.repo_full_name and i.day = d.day
left join pr_daily p on p.repo_full_name = d.repo_full_name and p.day = d.day
left join comment_daily c on c.repo_full_name = d.repo_full_name and c.day = d.day