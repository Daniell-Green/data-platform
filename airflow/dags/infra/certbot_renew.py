from __future__ import annotations

from datetime import datetime
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

    certbot_renew = BashOperator(
        task_id="certbot_renew",
        bash_command="""
        set -euo pipefail

        docker compose run --rm certbot renew \
          --non-interactive \
          --deploy-hook "echo renewed"
        """,
    )

    nginx_reload = BashOperator(
        task_id="nginx_reload",
        bash_command="""
        set -euo pipefail

        docker compose exec nginx nginx -s reload
        """,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    certbot_renew >> nginx_reload
