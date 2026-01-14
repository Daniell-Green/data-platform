from __future__ import annotations
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.bash import BashOperator
from docker.types import Mount
from airflow.models import Variable

DEFAULT_DBT_PROJECT_DIR_HOST = "/home/af_appuser/data-platform/dbt/data_transformation"

DEFAULT_DBT_ENV = {
    "DBT_PROFILES_DIR": "/usr/app",
    "DBT_DEV_TYPE": "postgres",
    "DBT_DEV_HOST": Variable.get("DBT_DEV_HOST"),
    "DBT_DEV_PORT": Variable.get("DBT_DEV_PORT"),
    "DBT_DEV_DBNAME": "dwh",
    "DBT_DEV_SCHEMA": "staging",
    "DBT_DEV_USER": Variable.get("DBT_DEV_USER"),
    "DBT_DEV_PASSWORD": Variable.get("DBT_DEV_PASSWORD")
}

def make_dbt_task(
    *,
    task_id: str,
    command: str,
    project_dir_host: str,
    network_mode: str = "data-platform",
    image: str = "ghcr.io/dbt-labs/dbt-postgres:1.9.latest",
) -> DockerOperator:
    env = dict(DEFAULT_DBT_ENV)
    return DockerOperator(
        task_id=task_id,
        image=image,
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode=network_mode,
        working_dir="/usr/app",
        mounts=[
            Mount(target="/usr/app", source=project_dir_host, type="bind"),
        ],
        environment=env,
        mount_tmp_dir=False,          # avoids /tmp/airflowtmp... bind mount failure
        entrypoint="/bin/sh",         # so "sh" isn't treated as a dbt command
        command=f'-lc "mkdir -p /root/.dbt && cp /usr/app/profiles.yml /root/.dbt/profiles.yml && {command}"',
    )


def dbt_run(*, project_dir_host: str = DEFAULT_DBT_PROJECT_DIR_HOST, select: str | None = None,) -> DockerOperator:
    cmd = "dbt run" + (f" --select {select}" if select else "")
    return make_dbt_task(task_id="dbt_run", command=cmd, project_dir_host=project_dir_host)


def dbt_test(*, project_dir_host: str = DEFAULT_DBT_PROJECT_DIR_HOST, select: str | None = None,) -> DockerOperator:
    cmd = "dbt test" + (f" --select {select}" if select else "")
    return make_dbt_task(task_id="dbt_test", command=cmd, project_dir_host=project_dir_host)


def dbt_docs_generate(*, project_dir_host: str = DEFAULT_DBT_PROJECT_DIR_HOST,) -> DockerOperator:
    return make_dbt_task(task_id="dbt_docs_generate", command="dbt docs generate", project_dir_host=project_dir_host)


def dbt_docs_publish(
    *,
    task_id: str = "publish_docs",
    project_dir_host: str = DEFAULT_DBT_PROJECT_DIR_HOST,
    publish_dir: str = "/usr/share/nginx/html/dbt-docs",
) -> BashOperator:
    bash_command = f"""
        bash -lc '
            set -euo pipefail
            
            SRC_DIR="{project_dir_host}/target"
            PUBLISH_DIR="{publish_dir}"
            STAGING_DIR="{publish_dir}.staging"
            FINAL_DIR="{publish_dir}"
            
            test -f "$SRC_DIR/index.html"
            
            rm -rf "$STAGING_DIR"
            mkdir -p "$STAGING_DIR" "$FINAL_DIR"
            
            cp -a "$SRC_DIR/." "$STAGING_DIR/"
            
            if command -v rsync >/dev/null 2>&1; then
              rsync -r --delete --omit-dir-times --no-perms --no-owner --no-group --no-times "$STAGING_DIR/" "$FINAL_DIR/"
            else
              rm -rf "$FINAL_DIR"/*
              cp -r "$STAGING_DIR/." "$FINAL_DIR/"
            fi
            
            rm -rf "$STAGING_DIR"
            test -f "$FINAL_DIR/index.html"
        '
    """.strip()

    return BashOperator(task_id=task_id, bash_command=bash_command)
