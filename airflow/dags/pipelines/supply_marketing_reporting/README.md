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
| `dbt/data_transformation/models/marts/supply_marketing/` | `fct_sm_sales`, `dim_sm_*`, `mart_sm_data_quality` |

## Running it

Trigger `supply_marketing_raw_ingest_transform` from the Airflow UI, or:

```bash
docker exec airflow-worker airflow dags trigger supply_marketing_raw_ingest_transform
```

Individual tasks, for debugging:

```bash
docker exec airflow-worker airflow tasks test supply_marketing_raw_ingest_transform load_raw_files 2026-08-12
docker exec airflow-worker airflow tasks test supply_marketing_raw_ingest_transform dbt_run    2026-08-12
docker exec airflow-worker airflow tasks test supply_marketing_raw_ingest_transform dbt_test   2026-08-12
```

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

**`fct_sm_sales` excludes flagged rows; `mart_sm_data_quality` reports them.**
Together they account for every source row. If you change one, check the other
still reconciles.

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

| Transaction | Flag | In KPIs? |
|---|---|---|
| 1009 | `missing_customer_id` | No |
| 1010 | `unknown_product_id` | No |
| 1012 | `negative_quantity` | No |
| 1007, 1008 | `possible_duplicate_transaction` | Yes — flagged for review, not excluded |

9 of 12 rows reach `fct_sm_sales`. 25 dbt tests pass.

Worth knowing when reading the dashboard: **Aral AG is the top customer entirely
on the strength of transactions 1007 and 1008.** If the business confirms those
are one booking, the ranking changes.
