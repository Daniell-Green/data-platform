# Server context — data-platform production host

Last verified: 2026-08-12, by direct SSH inspection of the live server. Cross-checked against `README.md` in this repo — matched exactly except where noted below.

## Access
- Host: `87.106.5.6` (hostname `ubuntu`)
- SSH: `root@87.106.5.6`, key-based (private key `id_rsa`)
- OS: Ubuntu 24.04.3 LTS, kernel 6.8.0-90-generic
- Hardware: 8 vCPU, 31GB RAM, 464GB disk (~12% used, 413GB free)
- Uptime at last check: 215+ days

## Deployment model
- **Docker Compose** stack lives on the server at `/home/af_appuser/data-platform/` (a checkout of this repo, owned by user `af_appuser`).
- **Kubernetes (kind)** cluster, managed via `abctl`, runs **only Airbyte**. Single node `airbyte-abctl-control-plane`.
  - kubectl client v1.36.3 / server v1.32.2 — version skew warning is cosmetic, not a real issue currently.
- **Nginx** (runs as a Docker container — there is no host-level `/etc/nginx`) terminates TLS for all public domains and proxies into the kind cluster over the external Docker network **`kind`**, reaching `airbyte-abctl-control-plane:31374` (the in-cluster ingress-nginx NodePort).

## Public domains (franklingreen.de, Let's Encrypt via Certbot)
All verified returning healthy responses on 2026-08-12:

| Domain | Purpose | Status |
|---|---|---|
| `airflow.franklingreen.de` | Airflow UI | 302 (login redirect, expected) |
| `metabase.franklingreen.de` | Metabase UI | 200 |
| `pgadmin.franklingreen.de` | pgAdmin UI | 302 (login redirect, expected) |
| `dbt-docs.franklingreen.de` | dbt docs site | 200 |
| `airbyte.franklingreen.de` | Airbyte UI & API | 200 |

Important ingress caveat (confirmed in README and in live config): the host-specific Airbyte ingress (`airbyte-franklingreen`, namespace `airbyte-abctl`) **must** include a `/` route to `airbyte-abctl-airbyte-server-svc:8001`, otherwise requests fall through to the wildcard ingress and return `403`.

## Docker Compose services (as of 2026-08-12, all "Up 6-7 months", no unexpected restarts)
- `nginx` (nginx:1.27-alpine) — reverse proxy, ports 80/443
- `airflow-webserver`, `airflow-scheduler`, `airflow-worker` (custom `data-platform-airflow-*` images)
- `postgres` (postgres:16) — primary warehouse; bound to `172.17.0.1:5432` (docker0 bridge only, not publicly exposed)
- `redis` (redis:7) — Airflow broker
- `pgadmin` (dpage/pgadmin4:8)
- `metabase` (metabase/metabase:v0.58.1)
- `dbt` (ghcr.io/dbt-labs/dbt-postgres:1.9.latest) — run via Airflow, container healthy
- Several `data-platform-certbot-run-*` one-shot containers (certbot/certbot:latest) — cert renewal runs; multiple still listed "Up" from 6-7 months ago even though they're one-shot jobs. Harmless but should be pruned eventually (`docker container prune`).

Docker version: 29.1.3 / Docker Compose v5.0.1.

## Kubernetes (kind) — namespace `airbyte-abctl`
All pods healthy, 214 days old, no unexpected restarts:
- `airbyte-abctl-server`, `airbyte-abctl-worker`, `airbyte-abctl-temporal`, `airbyte-abctl-cron`, `airbyte-abctl-connector-builder-server`, `airbyte-abctl-workload-api-server`
- `airbyte-abctl-workload-launcher` — 1 restart, 214 days ago (old, not a current concern)
- `airbyte-db-0` — Airbyte's own Postgres
- `airbyte-abctl-bootloader` — Completed (expected, one-shot init job)

Ingress objects: `airbyte-franklingreen` (class `nginx`, host `airbyte.franklingreen.de`) and `ingress-abctl` (wildcard default).

Other namespaces are all standard/expected: `ingress-nginx`, `default`, `kube-system`, `kube-node-lease`, `kube-public`, `local-path-storage`. Nothing unexpected.

## Data contract (Postgres)
Matches README exactly:
- `raw` schema — Airbyte writes here
- `staging` / `mart` schemas — dbt reads `raw`, writes both
- Metabase reads from `mart` only

## Host users
- `af_appuser` — owns the deployed repo checkout at `/home/af_appuser/data-platform/`; this is the account the platform runs as.
- `awny_vds` — a separate, unrelated user with its own SSH key and VS Code Remote session. No docker-compose or app files under its home — not part of the platform deployment.
- `root` — used for direct admin/ops work. Has `.kube/config`, `.airbyte/`, and various dev tool configs (`.claude`, `.copilot`, `.vscode-server`).

## Scheduling
- No crontab on `root`. Only standard Ubuntu systemd timers are active (apt-daily, logrotate, fstrim, sysstat, man-db, etc.) — nothing platform-specific.
- Certificate renewal does not appear to be cron-driven; the repeated one-shot certbot containers suggest it's triggered manually or by an external script/CI rather than an in-host scheduler. Worth confirming if automated renewal is actually wired up, since no timer or cron job was found driving it.

## Open items / things to watch
- kubectl client/server skew (1.36 vs 1.32) — bump client or pin an older kubectl if it starts causing real problems.
- Stale exited-but-"Up" certbot one-shot containers accumulating — safe to `docker container prune`.
- Confirm how/whether cert renewal is actually scheduled (no cron/timer found for it as of this check) — if it's not automated, certs could silently expire.
