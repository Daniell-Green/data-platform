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
- No direct reads of Airflow Variables or Connections at module import time

### Known deviation

`dbt_tasks.py` currently violates the last two principles: `DEFAULT_DBT_ENV` is a
module-level dict that calls `Variable.get()` four times as the module is imported.
Because Airflow re-parses DAG files on a timer, every parse issues those queries against
the metadata database for every DAG that imports this module — work that is repeated
constantly and only ever used when a task actually runs.

The fix is to resolve the variables inside `make_dbt_task()`, or to pass them as
templated strings (`{{ var.value.DBT_DEV_HOST }}`) so Airflow resolves them at execution
time. Recorded here rather than quietly dropped from the principles: the principle is
right and the code has not caught up with it.

## Responsibility

Code in this directory is **foundational**.
Changes here can affect many DAGs and should be made deliberately.