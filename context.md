# Server context — data-platform production host

Architecture and operational notes for the production deployment, verified by
direct inspection of the live server on 2026-08-12 and cross-checked against
`README.md`.

> **Scope note.** This repository is public, so this document deliberately
> records *architecture* and not *access*. Host addresses, account names, SSH
> details, OS build and patch levels, and pinned image digests are intentionally
> omitted — they are operational secrets that belong in a private runbook or a
> secrets manager, not in version control. Anyone who needs them has the private
> runbook.

## Deployment model
- **Docker Compose** stack lives on the server in a checkout of this repo, owned
  by a dedicated non-root application user. Administrative work is done
  separately from the account the platform runs as.
- **Kubernetes (kind)** cluster, managed via `abctl`, runs **only Airbyte**, on a
  single node (`airbyte-abctl-control-plane`).
- **Nginx** runs as a Docker container — there is no host-level `/etc/nginx`. It
  terminates TLS for all public domains and proxies into the kind cluster over
  the external Docker network **`kind`**, reaching the in-cluster ingress-nginx
  NodePort.

## Public domains (franklingreen.de, Let's Encrypt via Certbot)
All verified returning healthy responses on 2026-08-12:

| Domain | Purpose | Status |
|---|---|---|
| `airflow.franklingreen.de` | Airflow UI | 302 (login redirect, expected) |
| `metabase.franklingreen.de` | Metabase UI | 200 |
| `pgadmin.franklingreen.de` | pgAdmin UI | 302 (login redirect, expected) |
| `dbt-docs.franklingreen.de` | dbt docs site | 200 |
| `airbyte.franklingreen.de` | Airbyte UI & API | 200 |

Important ingress caveat (confirmed in README and in live config): the
host-specific Airbyte ingress (`airbyte-franklingreen`, namespace
`airbyte-abctl`) **must** include a `/` route to the Airbyte server service,
otherwise requests fall through to the wildcard ingress and return `403`.

## Docker Compose services
All running steadily with no unexpected restarts as of 2026-08-12:

- `nginx` — reverse proxy, terminates TLS on 80/443
- `airflow-webserver`, `airflow-scheduler`, `airflow-worker` — custom images
  built from `airflow/Dockerfile` in this repo
- `postgres` — primary warehouse; bound to the Docker bridge only and **not**
  publicly exposed
- `redis` — Airflow broker
- `pgadmin`
- `metabase`
- `dbt` — invoked by Airflow, container healthy
- Several one-shot `certbot` containers from past renewal runs

## Kubernetes (kind) — namespace `airbyte-abctl`
All pods healthy with no unexpected restarts: `airbyte-abctl-server`,
`-worker`, `-temporal`, `-cron`, `-connector-builder-server`,
`-workload-api-server`, `-workload-launcher`, plus `airbyte-db-0` (Airbyte's own
Postgres) and the completed `-bootloader` init job.

Ingress objects: `airbyte-franklingreen` (class `nginx`) and `ingress-abctl`
(wildcard default). All other namespaces are standard.

## Data contract (Postgres)
Matches README exactly:
- `raw` schema — Airbyte and Airflow ingestion write here
- `staging` / `mart` schemas — dbt reads `raw`, writes both
- Metabase reads from `mart` only, through a read-only role scoped to that schema

## Scheduling
- No platform-specific crontab. Only standard Ubuntu systemd timers are active
  (apt-daily, logrotate, fstrim, sysstat, man-db).
- Certificate renewal is **not** cron-driven — it is triggered by an **Airflow
  DAG**, which runs the one-shot certbot containers. Confirmed 2026-08-12.

## Open items / things to watch
- kubectl client/server version skew — bump the client or pin an older one if it
  starts causing real problems.
- Stale exited-but-"Up" certbot one-shot containers accumulating — safe to
  `docker container prune`.
- Airflow Variables currently hold database credentials. Moving them to a
  secrets backend is tracked in
  `airflow/dags/pipelines/supply_marketing_reporting/docs/governance.md`.
- Metabase has no `MB_ENCRYPTION_SECRET_KEY` set, so it stores its database
  connection credentials unencrypted in its application database. Setting one
  and restarting Metabase would encrypt them at rest.
