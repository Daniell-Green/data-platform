from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from shared.dbt_tasks import dbt_run, dbt_test, dbt_docs_generate, dbt_docs_publish

SOURCE_DIR = Path(__file__).parent / "source_data"
RAW_SCHEMA = "raw"

# Source file -> raw table name. Each file is loaded verbatim: no filtering,
# no corrections, no dedup. Data quality handling happens in dbt staging models,
# where it stays visible and testable instead of being silently applied on ingest.
SOURCE_FILES = {
    "sales.csv": "raw_sales",
    "Customers.xlsx": "raw_customers",
    "Products.xlsx": "raw_products",
    "Margin.xlsx": "raw_margin",
}


def _snake_case(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(name).strip()).lower()


def _engine():
    host = Variable.get("DBT_DEV_HOST")
    port = Variable.get("DBT_DEV_PORT")
    user = Variable.get("DBT_DEV_USER")
    password = Variable.get("DBT_DEV_PASSWORD")
    dbname = "dwh"
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}")


def load_raw_files() -> None:
    engine = _engine()
    loaded_at = datetime.utcnow()

    for filename, table_name in SOURCE_FILES.items():
        path = SOURCE_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Expected source file not found: {path}")

        if path.suffix == ".csv":
            df = pd.read_csv(path, sep=";", dtype=str)
        else:
            df = pd.read_excel(path, dtype=str)

        # Column names are lowercased/snake_cased so downstream SQL doesn't need
        # quoted mixed-case identifiers. This renames columns only — no value is
        # altered, filtered, or deduplicated on the way in.
        df.columns = [_snake_case(c) for c in df.columns]

        df["_source_file"] = filename
        df["_loaded_at"] = loaded_at

        df.to_sql(
            table_name,
            engine,
            schema=RAW_SCHEMA,
            if_exists="replace",
            index=False,
        )


with DAG(
    dag_id="supply_marketing_raw_ingest_transform",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # exercise data is static; trigger manually. See docs/governance.md for the productionized schedule proposal.
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2},
    tags=["supply_marketing_reporting", "raw", "dbt"],
) as dag:

    load_raw = PythonOperator(
        task_id="load_raw_files",
        python_callable=load_raw_files,
    )

    run = dbt_run(select="tag:supply_marketing_reporting")
    test = dbt_test(select="tag:supply_marketing_reporting")
    docs_gen = dbt_docs_generate()
    docs_pub = dbt_docs_publish()

    load_raw >> run >> test >> docs_gen >> docs_pub
