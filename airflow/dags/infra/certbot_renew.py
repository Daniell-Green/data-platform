from __future__ import annotations

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
}

with DAG(
    dag_id="certbot_renew",
    start_date=datetime(2025, 1, 1),
    schedule="0 3 * * *",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["infra", "tls", "certbot"],
) as dag:

    COMPOSE_FILE = "/home/af_appuser/data-platform/docker-compose.yml"
    COMPOSE_DIR = "/home/af_appuser/data-platform"

    certbot_renew = BashOperator(
        task_id="certbot_renew",
        bash_command=f"""
        set -euo pipefail
        timeout 300 docker compose -f {COMPOSE_FILE} --project-directory {COMPOSE_DIR} \
          run --rm --no-deps certbot renew --webroot -w /var/www/certbot --non-interactive
        """,
        execution_timeout=timedelta(minutes=6),
    )

    nginx_reload = BashOperator(
        task_id="nginx_reload",
        bash_command=f"""
        set -euo pipefail
        docker compose -f {COMPOSE_FILE} --project-directory {COMPOSE_DIR} \
          exec nginx nginx -s reload
        """,
        execution_timeout=timedelta(minutes=2),
    )

    certbot_renew >> nginx_reload
