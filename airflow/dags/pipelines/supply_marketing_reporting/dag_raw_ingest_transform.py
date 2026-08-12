from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, inspect

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from shared.dbt_tasks import dbt_build, dbt_docs_generate, dbt_docs_publish

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
    # Ingestion connects as the airflow role, not the dbt role: dbt holds only
    # USAGE + SELECT on raw so the transformation layer cannot rewrite its own
    # sources. See setup/grants.sql.
    host = Variable.get("DBT_DEV_HOST")
    port = Variable.get("DBT_DEV_PORT")
    user = Variable.get("RAW_DB_USER")
    password = Variable.get("RAW_DB_PASSWORD")
    dbname = "dwh"
    return create_engine(
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{dbname}"
    )


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

        # Truncate-and-append rather than pandas' "replace", which drops the
        # table: the dbt staging views depend on these tables, so a drop fails
        # once the models have been built. Truncating keeps the table and its
        # dependents in place while still giving full-refresh semantics.
        #
        # The truncate and the load share one transaction. Committing the
        # truncate separately would mean a failed load leaves the raw table
        # empty but committed, and the next dbt run would rebuild the marts to
        # zero rows while every task still reported success. Rolling back
        # together keeps the previous contents on any failure.
        with engine.begin() as conn:
            if inspect(conn).has_table(table_name, schema=RAW_SCHEMA):
                conn.exec_driver_sql(f'truncate table {RAW_SCHEMA}."{table_name}"')
                if_exists = "append"
            else:
                if_exists = "replace"

            df.to_sql(
                table_name,
                conn,
                schema=RAW_SCHEMA,
                if_exists=if_exists,
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

    # dbt build, not run-then-test: tests execute per model and anything downstream
    # of a failure is skipped. mart_sm_pipeline_status depends on the fact, so it is
    # only rebuilt when the marts actually pass validation - that is what makes its
    # validated_at timestamp meaningful to the dashboard.
    build = dbt_build(select="tag:supply_marketing_reporting")
    docs_gen = dbt_docs_generate()
    docs_pub = dbt_docs_publish()

    load_raw >> build >> docs_gen >> docs_pub
