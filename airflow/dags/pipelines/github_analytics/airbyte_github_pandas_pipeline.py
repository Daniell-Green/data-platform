from __future__ import annotations

from datetime import datetime
import time
import requests

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from shared.dbt_tasks import dbt_run, dbt_test, dbt_docs_generate, dbt_docs_publish

AIRBYTE_BASE_URL = "https://airbyte.franklingreen.de"
AIRBYTE_CONNECTION_ID = Variable.get("AIRBYTE_CONNECTION_ID")


def airbyte_sync_and_wait(connection_id: str, poke_interval: int = 15, timeout: int = 60 * 60) -> None:
    base = AIRBYTE_BASE_URL

    client_id = Variable.get("AIRBYTE_CLIENT_ID")
    client_secret = Variable.get("AIRBYTE_CLIENT_SECRET")

    s = requests.Session()

    def get_token() -> str:
        r = s.post(
            base + "/api/public/v1/applications/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Token request failed: {r.status_code} {r.text[:500]}")
        return r.json()["access_token"]

    token = get_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    r = s.post(
        base + "/api/v1/connections/sync",
        json={"connectionId": connection_id},
        headers=headers,
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Sync trigger failed: {r.status_code} {r.text[:500]}")
    job_id = r.json()["job"]["id"]

    start = time.time()
    while True:
        if int(time.time() - start) % 600 == 0 and int(time.time() - start) != 0:
            token = get_token()
            headers["Authorization"] = f"Bearer {token}"

        r = s.post(base + "/api/v1/jobs/get", json={"id": job_id}, headers=headers, timeout=30)

        if r.status_code == 401:
            token = get_token()
            headers["Authorization"] = f"Bearer {token}"
            r = s.post(base + "/api/v1/jobs/get", json={"id": job_id}, headers=headers, timeout=30)

        if r.status_code != 200:
            raise RuntimeError(f"Job status check failed: {r.status_code} {r.text[:500]}")

        status = r.json()["job"]["status"]
        if status in ("succeeded", "failed", "cancelled"):
            if status != "succeeded":
                raise RuntimeError(f"Airbyte job {job_id} ended with status={status}")
            return

        if time.time() - start > timeout:
            raise TimeoutError(f"Timed out waiting for Airbyte job {job_id}")

        time.sleep(poke_interval)


with DAG(
    dag_id="airbyte_then_dbt",
    start_date=datetime(2025, 1, 1),
    schedule='0 4 * * *',
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2},
    tags=["airbyte", "dbt"],
) as dag:

    airbyte_sync = PythonOperator(
        task_id="airbyte_sync_and_wait",
        python_callable=airbyte_sync_and_wait,
        op_kwargs={"connection_id": AIRBYTE_CONNECTION_ID, "poke_interval": 15, "timeout": 60 * 60},
    )

    run = dbt_run()
    test = dbt_test(select="tag:core")   # or None to run all tests
    docs_gen = dbt_docs_generate()
    docs_pub = dbt_docs_publish()

    airbyte_sync >> run >> test >> docs_gen >> docs_pub