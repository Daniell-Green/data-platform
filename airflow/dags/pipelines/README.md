# Data Pipelines

This directory contains **business and data-product pipelines**.

Each pipeline represents a meaningful data workflow that produces
tables, metrics, or artifacts consumed by downstream systems.

## What belongs here
- Airbyte ingestion + dbt transformation flows
- Domain-specific data products
- Analytics pipelines
- dbt runs, tests, and docs publishing

## Structure
Pipelines should be grouped by **domain or source**, not by technology.

Example:
- pipelines/
- github_analytics/
- dag_github_ingest_transform.py

## Characteristics
- Deterministic and reproducible
- Fail on data quality issues
- Produce durable outputs (tables, docs)
- Clearly owned and documented

## Typical pattern
1. Ingest data (Airbyte)
2. Transform data (dbt)
3. Validate data (dbt tests)
4. Publish artifacts (dbt docs, marts)

Pipeline DAGs should remain thin and delegate logic to `shared/`.
