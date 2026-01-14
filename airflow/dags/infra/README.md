# Infrastructure DAGs

This directory contains **infrastructure and platform maintenance DAGs**.

These DAGs do **not** represent business or data pipelines.  
They orchestrate operational tasks required to keep the platform healthy.

## What belongs here
- TLS / certificate renewal (Certbot)
- Backups and restores
- Cleanup / housekeeping jobs
- Platform-level maintenance
- Low-level operational automation

## What does NOT belong here
- Data ingestion pipelines
- Transformations (dbt)
- Business logic
- Analytics workflows

## Characteristics
- Idempotent
- Safe to re-run
- Minimal side effects
- Typically low-frequency (daily / weekly)

## Examples
- `certbot_renew`
- `postgres_backup`
- `log_cleanup`

Infra DAGs may interact with Docker, Kubernetes, or the host system.
