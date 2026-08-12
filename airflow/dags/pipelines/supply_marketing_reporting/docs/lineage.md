# Data Lineage — Source to KPI

## End-to-end flow

```mermaid
flowchart TD
    subgraph Source
        A1["sales.csv"]
        A2["Customers.xlsx"]
        A3["Products.xlsx"]
        A4["Margin.xlsx"]
    end

    subgraph Ingestion["Airflow · load_raw_files"]
        B["pandas read + snake_case columns<br/>no filtering, no corrections"]
    end

    subgraph Raw["Postgres · raw schema (owner: airflow)"]
        C1["raw_sales"]
        C2["raw_customers"]
        C3["raw_products"]
        C4["raw_margin"]
    end

    subgraph Staging["Postgres · staging schema (dbt views)"]
        D1["stg_sm_sales<br/>dq_valid + dq_issues"]
        D2["stg_sm_customers<br/>duplicate-name flag"]
        D3["stg_sm_products<br/>deduplicated key"]
        D4["stg_sm_margin"]
    end

    subgraph Mart["Postgres · mart schema (dbt tables)"]
        E1["fct_sm_sales<br/>every row + dq_valid"]
        E2["dim_sm_customer"]
        E3["dim_sm_product"]
        E4["dim_sm_date"]
        E5["mart_sm_data_quality<br/>flagged transactions"]
        E6["mart_sm_quality_issues<br/>all issues, all grains"]
        E7["mart_sm_pipeline_status<br/>validation freshness"]
    end

    subgraph BI["Metabase"]
        F["Supply & Marketing dashboard"]
    end

    A1 --> B
    A2 --> B
    A3 --> B
    A4 --> B
    B --> C1 & C2 & C3 & C4
    C1 --> D1
    C2 --> D2
    C3 --> D3
    C4 --> D4
    D2 --> D1
    D3 --> D1
    D1 --> E1
    D2 --> E2
    D3 --> E3
    D4 --> E3
    D1 --> E4
    D1 --> E5
    D1 --> E6
    E2 --> E6
    E3 --> E6
    E1 --> E7
    E2 --> E7
    E3 --> E7
    E1 & E2 & E3 & E4 & E5 & E6 & E7 --> F
```

`mart_sm_quality_issues` reads the dimensions as well as staging, because master data
problems (`C007`/`C008`, `P300`) live on the dimensions rather than on any transaction.
`mart_sm_pipeline_status` depends on the fact and both dimensions so that `dbt build`
skips it whenever their tests fail — that dependency is what makes its timestamp a
validation signal rather than a run timestamp.

`stg_sm_customers` and `stg_sm_products` feed back into `stg_sm_sales` because
the unknown-key checks test sales rows against the conformed master data.

## Worked example: "Revenue by country — Germany"

| Stage | Artefact | What happens | Value |
|---|---|---|---|
| Source file | `sales.csv` | 12 rows, `;` separated, `DD.MM.YYYY` dates | 12 rows |
| Raw dataset | `raw.raw_sales` | Loaded verbatim, all columns text, `_source_file` / `_loaded_at` added | 12 rows |
| Transformation | `staging.stg_sm_sales` | Types cast, dates parsed, quality rules applied. 1009, 1010 and 1012 marked `dq_valid = false`; 1007/1008 flagged but kept valid | 12 rows, 9 valid |
| Reporting model | `mart.fct_sm_sales` | Every row retained, `revenue = quantity * unit_price`, unresolvable keys routed to `-1` | 12 rows, 9 with `dq_valid = true` |
| Dashboard | Metabase "Revenue by Transaction Country" | `sum(revenue) group by transaction_country`, with the `dq_valid` filter at its default | DE 361,600 |
| KPI | Revenue — Germany | | **361,600 EUR** |

Reconciliation for DE: 52,000 + 41,600 + 36,000 + 90,000 + 90,000 + 52,000 = 361,600.

Note where the filtering happens: the fact table carries all 12 rows, and the dashboard
applies `dq_valid = true`. Clearing that filter raises Germany to 374,000 — the same
model, a different question.

The flagged German rows are visible in the data quality view: 1009 (15,600 missing
customer), 1010 (4,000 unknown product) and 1012 (7,200 negative quantity). Germany's
reported revenue is therefore 361,600 with 26,800 identified and accounted for, not
silently lost. All three flagged transactions happen to be German, so the 26,800 here is
the same figure as the platform-wide "Revenue Excluded by Data Quality" KPI.

The 374,000 is not 361,600 + 26,800, because 1012 carries a negative quantity and
subtracts. "Revenue excluded" uses absolute value deliberately: it measures exposure,
not a reconciling difference.

## Lineage in tooling

dbt resolves every dependency above through `ref()` and `source()`, so
`dbt docs generate` produces a navigable lineage graph. The pipeline publishes it
to nginx on each run, and the Metabase dashboard is registered as a dbt exposure
so the graph extends from source file to dashboard rather than stopping at the
mart.
