# Automation & Governance

How this solution would be productionised. The pipeline already runs end to end
on the platform; this covers what changes when the source stops being four files
on a laptop.

## Data ingestion

Today the DAG reads the four files from the repository, which is right for a
fixed exercise dataset but wrong for production: the data is versioned with the
code, and refreshing it means a commit.

In production the source would be either the upstream system directly (SAP
extract via JDBC/OData, which is where this data actually originates) or a
landing zone the business drops files into (SFTP or S3/MinIO). With a landing
zone the ingestion becomes an Airbyte connection instead of a Python task, which
is the pattern the platform already uses for its GitHub pipeline.

Whichever the source, the raw layer keeps its contract: **land data verbatim.**
No filtering, no corrections, no deduplication on the way in. That is what makes
it possible to prove later what the source actually said.

Two changes would be needed for repeated loads:

- **Full-refresh-on-load becomes incremental.** Ingestion currently truncates the
  raw table and re-appends the whole file, which is right for a static extract
  and wrong for a growing table. Sales would become an incremental dbt model
  keyed on `transaction_id`, with raw appending each batch rather than replacing
  the table's entire contents.
- **Every load gets a batch identifier.** `_loaded_at` and `_source_file` exist
  today; a `_batch_id` would let a single bad load be isolated and reverted.

## Refresh process

- **Schedule:** daily, early morning, after the upstream extract lands. The DAG
  is currently `schedule=None` because the exercise data is static.
- **Ordering:** ingest → `dbt run` → `dbt test` → `dbt docs generate` →
  publish docs. Already implemented.
- **Idempotency:** re-running a day must not double-count. This is why the fact
  table would be keyed on the source transaction ID rather than an ingestion
  surrogate.
- **Backfill:** `catchup=False` with `max_active_runs=1` today. A backfill would
  be an explicit, bounded operation, not something that starts by accident.

## Error handling

Two failure classes, deliberately handled differently:

**Pipeline failures** — the source file is missing, the database is unreachable,
a model does not compile. These fail loudly and stop the run. Retries (currently
2) cover transient problems; a genuine failure leaves the previous good data in
place rather than publishing a partial refresh.

**Data quality failures** — the data arrived but is not trustworthy. These do
*not* stop the pipeline. Rows are flagged, excluded from KPIs, and reported in
the data quality view. A pipeline that halts on a single bad row leaves the
business with no dashboard at all, which is usually worse than a dashboard that
is explicit about what it excluded.

The line between them is a judgement call and should be reviewed with the
business. A reasonable escalation: if the flagged share of revenue exceeds an
agreed threshold, treat it as a pipeline failure, because at that point the
dashboard is no longer representative.

## Monitoring

- **Freshness:** alert when the marts have not rebuilt within the expected
  window. A silently stale dashboard is more dangerous than a visibly broken one.
- **Volume:** alert on row counts departing materially from the recent norm, in
  both directions — a truncated extract and a duplicated one both show up here.
- **Quality trend:** track flagged rows and flagged revenue over time. A single
  bad row is noise; a rising trend means something upstream changed.
- **Test results:** `dbt test` failures should notify the owner, not just turn
  the Airflow task red.
- **Delivery:** email or Slack to a named owner. Alerts nobody receives are not
  monitoring.

## Security considerations

- **Least privilege by layer, already enforced.** `raw` is written by ingestion
  roles (`airbyte`, `airflow`); `dbt` holds only `USAGE` + `SELECT` there, so the
  transformation layer cannot rewrite its own sources. `dbt` owns `staging` and
  `mart`. Metabase connects as `metabase_ro`, which is read-only and scoped to
  `mart` — the BI tool cannot reach raw or staging at all. See
  `../setup/grants.sql`.
- **Credentials** live in Airflow Variables, not in the repository. dbt reads
  them from environment variables injected at run time.
- **Transport:** services are published behind nginx with Let's Encrypt
  certificates, renewed by a scheduled DAG.
- **Improvements worth making:**
  - Ingestion currently reuses the `airflow` role, which is also the Airflow
    metadata database owner. A dedicated `ingest` role scoped to `raw` would be
    a cleaner separation.
  - Airflow Variables holding secrets should move to a secrets backend
    (Vault, or the cloud provider's secret manager) so they are neither visible
    in the Airflow UI nor exportable by anyone with UI access.
  - Personal data: this dataset is B2B and carries none. If customer contacts
    were added, the raw layer would need retention rules and access restricted
    beyond the current model.

## Ownership and governance model

| Role | Responsibility |
|---|---|
| Business owner (Supply & Marketing) | Defines KPIs, approves measure definitions, decides master-data questions the pipeline deliberately does not answer — such as whether C007 and C008 are the same company |
| Data owner / steward | Accountable for source data correctness, drives fixes upstream in SAP rather than downstream in dbt |
| Data engineer | Owns the pipeline, models, tests and this documentation |
| BI / analytics | Owns the dashboard and how the measures are presented |
| Platform | Owns the infrastructure the pipeline runs on |

Working principles:

- **Downstream fixes are mitigations, not solutions.** Every flag in the data
  quality view is a ticket for the source system. If the same issue is still
  being worked around in six months, the governance process has failed even
  though the dashboard looks fine.
- **Measure definitions are versioned with the code.** Revenue means one thing,
  defined in one model, reviewed like any other change.
- **Changes go through pull requests.** The tests in `staging.yml` and
  `marts.yml` are the contract; a change that breaks them is a change that needs
  a conversation.
- **The data quality view is a standing agenda item**, not a debugging tool.
  It exists so the business sees what was excluded and why, every time they look
  at the numbers.
