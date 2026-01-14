# data-platform (self-hosted)

A self-hosted analytics and data engineering platform running on a single Ubuntu server.  
The platform is orchestrated with **Docker Compose** and uses an **abctl-managed Kubernetes (kind) cluster** to run Airbyte.

It provides end-to-end ingestion, transformation, orchestration, and analytics with a clear separation between configuration, secrets, and runtime state.

---

## High-level architecture

### Ingestion
- **Airbyte**
  - Installed via `abctl`
  - Runs inside a Kubernetes cluster (kind)

### Storage / Warehouse
- **PostgreSQL 16**
  - Primary analytical database
  - Explicit schema and role separation

### Transformation
- **dbt**
  - Containerized
  - Executed via Airflow
  - Generates documentation served by Nginx

### Orchestration
- **Airflow**
  - Scheduler, webserver, workers
  - Triggers Airbyte syncs and dbt runs

### BI / Analytics
- **Metabase**
  - Read-only access to curated marts

### Reverse proxy / TLS
- **Nginx**
  - Routes all public traffic
  - Terminates TLS using Let’s Encrypt (Certbot)

---

## Services & URLs

Public subdomains exposed via **Nginx + Let’s Encrypt**:

- `https://airflow.<domain>` – Airflow UI
- `https://airbyte.<domain>` – Airbyte UI & API  
  - health check: `https://airbyte.<domain>/api/v1/health`
- `https://metabase.<domain>` – Metabase UI
- `https://pgadmin.<domain>` – pgAdmin UI
- `https://dbt-docs.<domain>` – dbt documentation site

---

## Airbyte deployment details (abctl / Kubernetes / kind)

### Cluster
- Airbyte namespace: `airbyte-abctl`
- Kubernetes cluster: **kind**
- Kind node container:
  - `airbyte-abctl-control-plane`

### kubeconfig
- Primary:
  - `/root/.airbyte/abctl/abctl.kubeconfig`
- Copied to:
  - `/root/.kube/config` for standard `kubectl` usage

### Ingress
- Ingress controller: **ingress-nginx** (in-cluster)
- Ingress class: `nginx`

### Public exposure (stable, no port-forwarding)

Traffic flow:

```
Internet
  → Nginx (Docker, TLS termination)
  → kind NodePort
  → ingress-nginx
  → Airbyte services
```

**NodePorts (ingress-nginx service)**:
- HTTP: `31374`
- HTTPS: `31491`

### Host-specific Airbyte ingress

- Ingress name: `airbyte-franklingreen`
- Namespace: `airbyte-abctl`
- Required routes:
  - `/` → `airbyte-abctl-airbyte-server-svc:8001`
  - `/api/v1/connector_builder`
    → `airbyte-abctl-airbyte-connector-builder-server-svc:80`

**Important**  
If a host-specific ingress is defined, it **must** include a `/` route.  
Otherwise, requests may fall through to the wildcard ingress and return `403`.

---

## Nginx ↔ kind networking dependency

- The `nginx` container must be attached to the Docker network **`kind`**
- This allows Nginx to reach:
  - `airbyte-abctl-control-plane:31374`

This is declared explicitly in `docker-compose.yml` as an external network.

---

## Airflow ↔ Airbyte connectivity

- Airflow uses the public Airbyte base URL:
  - `https://airbyte.<domain>`
- No host port-forwarding is used (deprecated in this setup)

---

## Data contract (Postgres schemas & roles)

### Schemas
- `raw`
- `staging`
- `mart`

### Responsibilities
- **Airbyte** → writes to `raw`
- **dbt** → reads `raw`, writes `staging` and `mart`
- **Metabase** → reads from `mart` only

Roles are explicitly managed with schema-level privileges
(`USAGE`, `SELECT`, `CREATE` as appropriate).

---

## Project structure (recommended)

```
data-platform/
├─ docker-compose.yml
├─ .env
├─ README.md
├─ airflow/
│  ├─ .env
│  ├─ dags/
│  ├─ plugins/
│  ├─ docs/
│  └─ logs/
├─ certbot/
│  ├─ conf/
│  ├─ logs/
│  └─ www/
├─ dbt/
│  └─ <PROJECT>/
│     ├─ analysis/
│     ├─ macros/
│     ├─ models/
│     ├─ seeds/
│     ├─ snapshots/
│     ├─ tests/
│     ├─ target/
│     ├─ profiles.yml
│     └─ dbt_project.yml
├─ kubernetes/
│  └─ airbyte/
│     └─ airbyte-ingress.yml
├─ nginx/
│  ├─ conf.d/
│  └─ www/
│     └─ dbt-docs/
├─ pgadmin/
│  └─ servers.json
└─ postgres/
   └─ init/
```

---

## Common operations

### Docker Compose (platform services)

Start:
```bash
docker compose up -d
```

Inspect:
```bash
docker compose ps
docker compose logs -f --tail=200 <service>
```

### Kubernetes (Airbyte)

Set kubeconfig:
```bash
export KUBECONFIG=/root/.airbyte/abctl/abctl.kubeconfig
```

Inspect cluster:
```bash
kubectl -n airbyte-abctl get pods
kubectl -n airbyte-abctl get svc
kubectl -n airbyte-abctl get ingress
kubectl -n ingress-nginx get svc ingress-nginx-controller
```

Verify Airbyte:
```bash
curl -i https://airbyte.<domain>/api/v1/health
```

---

## Airflow DAGs (current state)

Pipeline pattern:
1. Airbyte sync ✅
2. dbt run ✅
3. dbt test ⏳
4. dbt docs publish ✅

Notes:
- `dbt test` should fail the DAG on test failures
- Prefer model/test selection via tags

---

## dbt docs publishing

A DAG exists to publish dbt docs to Nginx.

Stabilization target:
- atomic deploy (staging directory → final)
- Nginx serves a fully consistent docs site at all times

---

## Portfolio demo status

### Current dataset
- Airbyte ingesting GitHub data from: `pandas-dev/pandas`

### Metabase
- One dashboard with two cards:
  - time series: commits / PRs / comments
  - table: top repositories by PR count

### Planned improvements
- additional marts (lead time, backlog, contributor activity)
- dbt tests & documentation coverage
- expanded dashboards with insight metrics (e.g. PR lead time)

---

## Troubleshooting

### kubectl connects to localhost:8080

Fix:
```bash
export KUBECONFIG=/root/.airbyte/abctl/abctl.kubeconfig
cp /root/.airbyte/abctl/abctl.kubeconfig /root/.kube/config
chmod 600 /root/.kube/config
```

### Airbyte returns 403 after ingress changes

Cause:
- Host-specific ingress without `/` route

Fix:
- Ensure `/` routes to `airbyte-abctl-airbyte-server-svc`

### Nginx cannot reach Airbyte

Cause:
- Nginx not attached to Docker network `kind`

Fix:
- Add `kind` as an external network to the nginx service

---

## Security notes

- Secrets are never committed
- `.env` files are ignored
- Metabase uses read-only database access
- Postgres roles enforce schema boundaries
