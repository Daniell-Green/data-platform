# Supply & Marketing Reporting

Reporting pipeline for the Supply & Marketing department: revenue by country,
volume by product, margin by product group, top customers, and revenue trends —
with a data quality view showing what the KPIs exclude and why.

## What this pipeline does

```
source files -> raw (verbatim) -> staging (typed + quality flags) -> mart (star schema) -> Metabase
```

The guiding rule: **raw never changes, staging never drops.** Source data lands
untouched, quality problems are flagged rather than silently corrected, and only
the mart layer decides what to exclude from headline numbers.

## Layout

| Path | Contents |
|---|---|
| `dag_raw_ingest_transform.py` | Airflow DAG: loads source files into `raw`, then runs dbt |
| `source_data/` | The four source files (exercise dataset; see caveat below) |
| `setup/grants.sql` | Database privileges this pipeline requires, run once as admin |
| `docs/data_assessment.md` | Quality issues found, assumptions, risks, remediation |
| `docs/data_model.md` | Star schema, measures, design decisions |
| `docs/lineage.md` | Source-to-KPI lineage with a worked reconciliation |
| `docs/governance.md` | Productionisation: refresh, error handling, monitoring, security, ownership |

dbt models live with the rest of the dbt project, not here:

| Path | Contents |
|---|---|
| `dbt/data_transformation/models/sources/supply_marketing.yml` | Source definitions for the `raw` tables |
| `dbt/data_transformation/models/staging/supply_marketing/` | `stg_sm_*` — typing, conforming, quality flags |
| `dbt/data_transformation/models/marts/supply_marketing/` | `fct_sm_sales`, `dim_sm_*`, `mart_sm_data_quality`, `mart_sm_quality_issues`, `mart_sm_pipeline_status` |
| `dbt/data_transformation/tests/` | `assert_sm_transaction_country_matches_customer.sql` |
| `setup/metabase_dq_filter.py` | Applies the dashboard's `dq_valid` filter and card definitions |

## Running it

Trigger `supply_marketing_raw_ingest_transform` from the Airflow UI, or:

```bash
docker exec airflow-worker airflow dags trigger supply_marketing_raw_ingest_transform
```

Individual tasks, for debugging:

```bash
docker exec airflow-worker airflow tasks test supply_marketing_raw_ingest_transform load_raw_files 2026-08-12
docker exec airflow-worker airflow tasks test supply_marketing_raw_ingest_transform dbt_build     2026-08-12
```

The transformation is a single `dbt build` task, not separate `dbt_run` and `dbt_test`
tasks. `build` tests each model as it is materialised and skips anything downstream of a
failure, so invalid data cannot reach a published table while every task still reports
success. See `docs/data_model.md` for why that matters to the freshness card.

The DAG is `schedule=None`: the exercise dataset is static, so there is nothing
to refresh on a timer. `docs/governance.md` covers the scheduling this would need
against a live source.

## Setup on a new environment

1. Apply the privileges: `psql -U admin -d dwh -f setup/grants.sql`
2. Set Airflow Variables `RAW_DB_USER` and `RAW_DB_PASSWORD` (the `airflow`
   database role), alongside the existing `DBT_DEV_*` variables.
3. Rebuild the Airflow image — it installs `openpyxl`, needed to read `.xlsx`.

## Things to know before changing this

**Ingestion connects as the `airflow` role, not `dbt`.** The `dbt` role has only
`USAGE` + `SELECT` on `raw`, so the transformation layer cannot rewrite its own
sources. Do not "fix" a permission error by granting `dbt` write access to `raw`;
that removes the boundary on purpose.

**Quality rules live in `stg_sm_sales`, in one place.** Adding a rule means
adding a reason code there — not filtering in a mart or in a Metabase question.
Marts consume `dq_valid`; they do not redefine it.

**`fct_sm_sales` contains every source row, flagged or not.** `dq_valid` marks the
rows fit for headline KPIs, and the dashboard filters on it — the model does not.
Do not add a `where dq_valid` back into the fact: that is what made the mart
unable to describe its own completeness, and made reclassifying a key-related
rule a breaking change instead of a one-line edit.

**`mart_sm_data_quality` and `mart_sm_quality_issues` report the problems.** The
first is transaction-grained detail; the second normalises every issue across
transactions, customers and products to one row per `(scope, entity, code)`. If
you change the rules in `stg_sm_sales`, check all three still reconcile.

**Two similar-looking problems are handled differently, deliberately.** The
duplicate `ProductID` is deduplicated (a duplicate dimension key fans out fact
rows — a structural defect). The near-identical customer names are kept and
flagged (both keys are valid; merging them is a business decision). The
reasoning is in `docs/data_assessment.md`.

**`source_data/` is an exercise convenience.** Versioning data with code is not a
production pattern — it means refreshing data requires a commit. Against a live
source this reads from SAP or a landing zone instead; see `docs/governance.md`.

## Verified behaviour

Against the current dataset (12 transactions), the pipeline flags exactly:

| Transaction | Flag | `dq_valid` | In headline KPIs? |
|---|---|---|---|
| 1009 | `missing_customer_id` | false | No |
| 1010 | `unknown_product_id` | false | No |
| 1012 | `negative_quantity` | false | No |
| 1007, 1008 | `possible_duplicate_transaction` | true | Yes — flagged for review, still counted |

Plus two master data flags that are not transaction-level:
`C007`/`C008` (`is_possible_duplicate_customer`) and `P300`
(`has_duplicate_source_rows`), reported through `mart_sm_quality_issues`.

**All 12 of 12 rows reach `fct_sm_sales`**; 9 carry `dq_valid = true` and are what the
dashboard shows by default. 33 dbt tests pass. Headline figures with the filter at its
default: revenue 501,500, volume 1,100, margin 18,000. Clearing the filter gives
513,900 / 1,160 / 18,150, and 26,800 is the absolute revenue carried by flagged rows.

Worth knowing when reading the dashboard: **Aral AG is the top customer entirely
on the strength of transactions 1007 and 1008.** If the business confirms those
are one booking, the ranking changes.
