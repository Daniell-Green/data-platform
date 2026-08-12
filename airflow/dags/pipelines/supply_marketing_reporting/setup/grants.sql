-- Privileges required by the supply_marketing_reporting pipeline.
-- Run once as a superuser (admin) against the dwh database.
--
-- The platform separates who writes raw data from who reads it: Airbyte owns the
-- raw schema, and the dbt role holds only USAGE + SELECT there. This pipeline
-- ingests through Airflow rather than Airbyte, so the airflow role - not dbt -
-- is granted write access. dbt stays a read-only consumer of raw, which keeps
-- the transformation layer unable to alter its own source data.

GRANT USAGE, CREATE ON SCHEMA raw TO airflow;

-- Tables this pipeline creates are owned by airflow, so dbt needs SELECT on them.
-- Default privileges cover tables created from now on; the explicit grant covers
-- any created before this script was run.
ALTER DEFAULT PRIVILEGES FOR ROLE airflow IN SCHEMA raw
    GRANT SELECT ON TABLES TO dbt;

GRANT SELECT ON ALL TABLES IN SCHEMA raw TO dbt;
