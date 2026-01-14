# Shared DAG Code

This directory contains **reusable Python code** shared across multiple DAGs.

It is treated as an **internal Python package**, not a place for DAG definitions.

---

## What belongs here

- Task factories (e.g. dbt, Airbyte helpers)
- Custom operators or operator wrappers
- Utilities (paths, logging, validation)
- Constants and configuration helpers

Examples:
- dbt task builders
- Airbyte trigger / sensor helpers
- Common retry or failure handling logic

---

## What does NOT belong here

- DAG definitions
- Scheduling logic
- Environment-specific configuration
- One-off helper scripts

If a file defines a DAG (`with DAG(...)`), it does **not** belong here.

---

## Design principles

- Importable and reusable
- No side effects at import time
- No direct reads of Airflow Variables or Connections at module im
