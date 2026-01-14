# Certbot – TLS Certificate Management

This directory contains the **Certbot setup for managing TLS certificates** (Let’s Encrypt) for the `franklingreen.de` subdomains used by the data platform.

Certificates are obtained via the **HTTP-01 challenge** and are consumed by **Nginx**.  
Only configuration and documentation live in Git — **never certificate state or private keys**.

---

## Managed Domains

Certificates are issued for the following domains:

- airflow.franklingreen.de
- airbyte.franklingreen.de
- metabase.franklingreen.de
- dbt.docs.franklingreen.de
- pgadmin.franklingreen.de

---

## Challenge Type

- **HTTP-01**
- Validation via port **80**
- Nginx serves the ACME challenge files from a shared volume

---

## Deployment Model

- Certbot runs as a **Docker container**
- Nginx runs as a **Docker container**
- Both containers share the required volumes for:
  - ACME challenges
  - Certificates

---

## Volume Layout

### Certbot container
```yaml
- ./certbot/www:/var/www/certbot
- ./certbot/conf:/etc/letsencrypt
- ./certbot/logs:/var/log/letsencrypt
```

### Nginx container
```yaml
- ./nginx/conf.d:/etc/nginx/conf.d:ro
- ./nginx/www:/usr/share/nginx/html:ro
- ./certbot/www:/var/www/certbot:ro
- ./certbot/conf:/etc/letsencrypt:ro
- ./nginx/.htpasswd_airbyte:/etc/nginx/.htpasswd_airbyte:ro
```

Nginx must expose /.well-known/acme-challenge/ from /var/www/certbot.

---

### Nginx Certificate Paths

Nginx is configured to load certificates from:
```
ssl_certificate     /etc/letsencrypt/live/<domain>/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/<domain>/privkey.pem;
```
These paths are populated automatically by Certbot.

---

### Initial Certificate Issuance

Run Certbot once to issue certificates:
```
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email hdf.green@gmail.com \
  --agree-tos \
  --no-eff-email \
  -d airflow.franklingreen.de \
  -d airbyte.franklingreen.de \
  -d metabase.franklingreen.de \
  -d dbt.docs.franklingreen.de \
  -d pgadmin.franklingreen.de
```
After successful issuance:
1. Reload Nginx
2. Verify HTTPS access

---

### Renewal Strategy
- External scheduler triggers renewal
- Command used:
```
docker compose run --rm certbot renew
```
Recommended frequency: twice daily
- Certbot will renew only when certificates are close to expiry
- After renewal, Nginx must be reloaded to pick up new certificates.

---

### What Must NEVER Be Committed

The following directories contain sensitive or host-specific state and must not be tracked by Git:

- certbot/conf/
- certbot/logs/
- certbot/www/
- Any live/, archive/, renewal/, or accounts/ data

If any private key is accidentally committed, revoke and re-issue certificates immediately.

---

### Git Hygiene

Recommended ``.gitignore`` rules:

```
certbot/**
!certbot/README.md
```

---

### Failure Recovery

If certificates are lost or corrupted:

1. Stop Nginx
2. Remove certbot/conf contents
3. Re-run initial issuance
4. Reload Nginx

Let’s Encrypt rate limits apply — avoid repeated failed runs.

---

### Notes
- Production environment (not staging)
- Email used for Let’s Encrypt registration:
```
hdf.green@gmail.com
```
Certificates are host-bound and not portable across servers