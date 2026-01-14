# Nginx – Reverse Proxy & TLS Termination

This directory contains the **Nginx configuration** for the `franklingreen.de` data platform.  
Nginx runs as a **Docker container**, acts as the **single entry point**, and is responsible for:

- Reverse proxying internal services
- TLS termination (Let’s Encrypt via Certbot)
- Serving static content (dbt docs)
- ACME challenge handling for certificate issuance/renewal

Only configuration is tracked in Git. **No secrets, certificates, or runtime state are committed.**

---

## Deployment Overview

- **Runtime**: Docker  
- **Container name**: `nginx`  
- **Image**: `nginx:1.27-alpine`  
- **Compose service**: `nginx`  
- **Docker network**: `data-platform`

Nginx communicates with upstream services via **Docker service names** on the shared network.

---

## Exposed Domains & Upstreams

| Domain                          | Type           | Upstream / Content Source |
|---------------------------------|----------------|----------------------------|
| airflow.franklingreen.de        | Reverse proxy  | `airflow-webserver:8080`   |
| airbyte.franklingreen.de        | Reverse proxy  | `airbyte-abctl-control-plane:31374` |
| metabase.franklingreen.de       | Reverse proxy  | `metabase:3000`            |
| pgadmin.franklingreen.de        | Reverse proxy  | `pgadmin:80`               |
| dbt.docs.franklingreen.de       | Static files   | `/usr/share/nginx/html/dbt-docs` |
| franklingreen.de (optional)     | Static files   | `/usr/share/nginx/html/index.html` |

Upstreams are defined using Nginx variables, for example:
```nginx
set $airflow_upstream airflow-webserver:8080;
set $metabase_upstream metabase:3000;
set $pgadmin_upstream pgadmin:80;
```

---

## TLS & Certificates

- **TLS termination**: Nginx  
- **Certificate provider**: Let’s Encrypt (Certbot)  

Certificate paths:
```nginx
/etc/letsencrypt/live/<domain>/fullchain.pem
/etc/letsencrypt/live/<domain>/privkey.pem
```

---

## ACME Challenge Handling

- **Challenge type**: HTTP-01  
- **Challenge path**: `/.well-known/acme-challenge/`  
- **Filesystem path**: `/var/www/certbot`  
- **Port 80**: Always open  

---

## Authentication

No authentication is currently enforced at the Nginx layer.

---

## Static Content

- dbt docs served from: `/usr/share/nginx/html/dbt-docs`  
- Optional static landing page for `franklingreen.de`

---

## Docker Networking

- **Network**: `data-platform`  
- **Addressing**: Docker service names  
- **depends_on**:
  - airflow-webserver
  - metabase
  - pgadmin

---

## Operational Tasks

### Reload Nginx
```bash
docker compose exec nginx nginx -s reload
```

### Add a new domain
1. Add server block in `nginx/conf.d/`
2. Add domain to Certbot issuance
3. Reload Nginx
4. Verify HTTPS

### Certificate renewal
```bash
docker compose run --rm certbot renew
docker compose exec nginx nginx -s reload
```

---

## What Must NOT Be Committed

- TLS certificates or keys
- Certbot state
- `.htpasswd` with real credentials
- Logs or cache files

---

## Responsibility

This configuration is production-critical infrastructure.
