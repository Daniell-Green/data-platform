from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {"owner": "airflow"}

DBT_CONTAINER = "dbt"
DBT_PROJECT_DIR = "/usr/app"

# nginx serves ./nginx/www -> /usr/share/nginx/html
PUBLISH_DIR = "/usr/share/nginx/html/dbt-docs"

with DAG(
    dag_id="dbt_docs_publish",
    start_date=datetime(2025, 1, 1),
    schedule=None,  # keep manual until stable
    catchup=False,
    default_args=DEFAULT_ARGS,
    max_active_runs=1,
    tags=["dbt", "docs"],
) as dag:

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"""
            set -euo pipefail
            
            docker inspect {DBT_CONTAINER} >/dev/null
            
            docker exec {DBT_CONTAINER} sh -lc "
              cd {DBT_PROJECT_DIR} &&
              dbt docs generate
            "
        """,
    )

    publish_docs = BashOperator(
        task_id="publish_docs",
        bash_command=f"""
            bash -lc '
            set -eu
            PUBLISH_DIR="{PUBLISH_DIR}"
            STAGING_DIR="{PUBLISH_DIR}.staging"
            FINAL_DIR="{PUBLISH_DIR}"
        
            rm -rf "$STAGING_DIR"
            mkdir -p "$STAGING_DIR" "$FINAL_DIR"
        
            docker cp {DBT_CONTAINER}:{DBT_PROJECT_DIR}/target/. "$STAGING_DIR/"
        
            if command -v rsync >/dev/null 2>&1; then
              rsync -a --delete "$STAGING_DIR/" "$FINAL_DIR/"
            else
              rm -rf "$FINAL_DIR"/*
              cp -a "$STAGING_DIR/." "$FINAL_DIR/"
            fi
        
            rm -rf "$STAGING_DIR"
            test -f "$FINAL_DIR/index.html"
        '""",
    )

    nginx_reload = BashOperator(
        task_id="nginx_reload",
        bash_command="""
            set -euo pipefail
            # optional: only if you actually need reload; nginx will serve static files without reload
            docker exec nginx nginx -s reload || true
        """,
    )

    dbt_docs_generate >> publish_docs >> nginx_reload
