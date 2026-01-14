Airbyte runs on kind (airbyte-abctl-control-plane)
Public access path: nginx → kind NodePort 31374 → ingress-nginx → airbyte services
If kind cluster is rebuilt, node container name/IP/nodeports may change (re-run kubectl -n ingress-nginx get svc and update nginx upstream if needed)

# data-platform (self-hosted)

A self-hosted analytics/data engineering platform running on an Ubuntu server using Docker Compose + an abctl-managed (kind) Kubernetes cluster for Airbyte. Includes Postgres, Airflow, dbt, Metabase, pgAdmin, Nginx reverse proxy with Let’s Encrypt, and supporting tooling.

---

## High-level architecture

**Ingestion**
- Airbyte (installed via `abctl`, running in Kubernetes/kind)

**Storage / Warehouse**
- Postgres 16 (primary platform database)

**Transformation**
- dbt (containerized; executed via Airflow)

**Orchestration**
- Airflow (scheduler/webserver/workers; triggers Airbyte syncs and dbt steps)

**BI**
- Metabase (reads from `mart` schema only)

**Reverse proxy / TLS**
- Nginx (routes subdomains, terminates TLS with Let’s Encrypt)

---

## Services & URLs

Public subdomains (behind Nginx + Let’s Encrypt):
- `https://airflow.<domain>` – Airflow UI
- `https://airbyte.<domain>` – Airbyte UI + API
  - health: `https://airbyte.<domain>/api/v1/health`
- `https://metabase.<domain>` – Metabase UI
- `https://pgadmin.<domain>` – pgAdmin UI
- `https://dbt-docs.<domain>` – dbt docs site

---

## Key implementation details

### Airbyte (abctl / Kubernetes / kind)
- Airbyte is deployed via `abctl` into the namespace: `airbyte-abctl`
- Kubernetes context (kubeconfig):
  - `/root/.airbyte/abctl/abctl.kubeconfig`
  - copied to `/root/.kube/config` for normal `kubectl` usage
- Cluster node container:
  - `airbyte-abctl-control-plane` (kind node)
- ingress-nginx is installed in-cluster and used for routing.

#### Airbyte exposure (stable, no port-forward)
We expose Airbyte via:
- `Ingress` resources inside k8s (`IngressClass: nginx`)
- Docker nginx reverse proxy (TLS) → kind node NodePort → ingress-nginx → airbyte services

**NodePorts (ingress-nginx service)**
- HTTP NodePort: `31374` (service port 8000 → NodePort 31374)
- HTTPS NodePort: `31491` (service port 443 → NodePort 31491)

**Airbyte host ingress (host-specific)**
- Ingress name: `airbyte-franklingreen` (namespace `airbyte-abctl`)
- Must include routing for:
  - `/` → `airbyte-abctl-airbyte-server-svc:8001` (serves Airbyte UI and API)
  - `/api/v1/connector_builder` → `airbyte-abctl-airbyte-connector-builder-server-svc:80`

**Important**
- Host-specific ingress takes precedence over wildcard ingress (`ingress-abctl`). If you define a host-specific ingress, include the `/` route, otherwise you may get `403`.

### Nginx ↔ kind Docker network dependency
- The `nginx` container must be attached to the Docker network `kind` so it can reach:
  - `airbyte-abctl-control-plane:31374`

This is declared in docker-compose (external network):
- `kind` external network is added to the nginx service in compose.

### Airflow ↔ Airbyte connectivity
- Airflow should use Airbyte base URL:
  - `https://airbyte.<domain>`
- Avoid any host port-forward approaches (deprecated in this setup).

---

## Data contract (Postgres roles & schemas)

Target contract:
- Airbyte writes only to `raw`
- dbt reads from `raw`, writes to `staging` and `mart`
- Metabase reads only from `mart`

Schemas:
- `raw`
- `staging`
- `mart`

Roles are explicitly managed with schema-level privileges (USAGE/SELECT/CREATE as appropriate).

---

## Project structure (recommended)

    data-platform/
        docker-compose.yml
        .env
        readme.md
        airflow/
            .env
            dags/
            plugins/
            docs/
            logs/
        certbot
            conf/
            logs/
            www/
        dbt/
            <PROJECT>/
                analysis/
                macros/ 
                models/
                seeds/
                snapshots/
                target/
                tests/
                profiles.yml
                dbt_project.yml
            logs/
            profiles/
        kubernetes/
            airbyte/
                airbyte-ingress.yml
        nginx/
            conf.d/
            www/
                dbt-docs/
        pgadmin/
            servers.json
        postgres/
            - init/

---

## Common operations

### Docker Compose (platform services)
Start:
```bash
docker compose up -d
```
Check:
```
docker compose ps
docker compose logs -f --tail=200 <service>
```
### Kubernetes (Airbyte)
Set kubeconfig (if needed):
```
export KUBECONFIG=/root/.airbyte/abctl/abctl.kubeconfig
```
Inspect:
```
kubectl -n airbyte-abctl get pods
kubectl -n airbyte-abctl get svc
kubectl -n airbyte-abctl get ingress
kubectl -n ingress-nginx get svc ingress-nginx-controller
```
### Verify Airbyte endpoint
```
curl -i https://airbyte.<domain>/api/v1/health
```

---

### Airflow DAGs (current state)
Pipeline pattern:

1. Airbyte sync (DONE)
2. dbt run (DONE)
3. dbt test (TODO)
4. dbt docs publish (DONE)

Notes: 

- ``dbt test`` should fail the DAG on test failures.
- Prefer tagging / selecting tests for performance and clarity.

---

## dbt docs publishing

A DAG exists to publish dbt docs.
Stabilization target:

- atomic deploy (release directory + current symlink)
- Nginx serves current/ to avoid partial publishes

---

## Portfolio demo status

Current dataset:

- Airbyte pulling GitHub repo: ``pandas-dev/pandas``

Metabase:

- 1 dashboard with 2 cards:
  - line chart: commits / PRs / comments
  - table: top 10 repositories by PRs

Next improvements:

- add marts (lead time, backlog, contributor activity)
- add dbt tests + docs coverage
- expand dashboard to 4–6 cards with at least one “insight metric” (e.g., PR lead time)

---

## Troubleshooting
kubectl connects to localhost:8080 / no context

Fix by pointing kubectl to abctl kubeconfig:

```
export KUBECONFIG=/root/.airbyte/abctl/abctl.kubeconfig
cp /root/.airbyte/abctl/abctl.kubeconfig /root/.kube/config
chmod 600 /root/.kube/config
```

### Airbyte UI/API returns 403 after ingress changes

Cause: host-specific ingress without a ``/`` route.

Fix: ensure host-specific ingress includes ``/`` backend routing to ``airbyte-abctl-airbyte-server-svc``.


### nginx cannot reach Airbyte (timeouts)

Cause: nginx not connected to Docker network ``kind``.

Fix: declare ``kind`` external network in compose for nginx.

---

## Security notes

- Keep secrets out of git:
  - use ``.env`` and ``env_file`` where possible
- Restrict public exposure to only required services.
- Metabase uses read-only DB role.
- Postgres roles enforce schema boundaries.



































