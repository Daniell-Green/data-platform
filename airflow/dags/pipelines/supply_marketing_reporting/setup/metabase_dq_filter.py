#!/usr/bin/env python3
"""Wire the "Data quality" filter into Metabase dashboard 3.

`fct_sm_sales` carries every source transaction, including rows that failed a
staging data quality rule. The decision about which rows count toward headline
KPIs now lives in the BI layer: one dashboard-level boolean field filter on
`fct_sm_sales.dq_valid`, defaulting to true, wired to the ten cards that read
the fact.

Run this AFTER the dbt models have been rebuilt and Metabase has re-synced the
`mart` schema -- the field filter needs `mart.fct_sm_sales.dq_valid` to exist as
a synced field. The script refuses to run if it cannot find it.

    export METABASE_API_KEY=...            # never commit this
    python metabase_dq_filter.py --dry-run
    python metabase_dq_filter.py --apply
    python metabase_dq_filter.py --revert backup_<timestamp>.json

Why the SQL is rewritten by hand rather than patched with a regex: a field
filter renders as a fully qualified `"mart"."fct_sm_sales"."dq_valid"`, so a
query that aliases the fact table (`from mart.fct_sm_sales f`) fails with
"missing FROM-clause entry". Cards 47-50 therefore drop the alias. Each
statement below is written out in full so the change is reviewable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get("METABASE_URL", "https://metabase.franklingreen.de")
DASHBOARD_ID = 3

TAG_NAME = "dq_valid"
PARAM_NAME = "Data quality"
PARAM_SLUG = "dq_valid"
PARAM_TYPE = "boolean/="
PARAM_ID = "dqvalid01"

# The ten cards that read mart.fct_sm_sales. The three data quality cards
# (44 Revenue Excluded, 51 Flagged Records, 52 Flagged Records by Issue) read
# mart_sm_data_quality and are deliberately left unwired: they must keep showing
# the flagged rows no matter what the rest of the dashboard is filtered to.
CARD_SQL = {
    40: "select sum(revenue) as total_revenue from mart.fct_sm_sales where {{dq_valid}}",
    41: "select sum(volume) as total_volume from mart.fct_sm_sales where {{dq_valid}}",
    42: "select sum(margin) as total_margin from mart.fct_sm_sales where {{dq_valid}}",
    43: (
        "select round(100.0 * sum(margin) / nullif(sum(revenue), 0), 1) as margin_pct "
        "from mart.fct_sm_sales where {{dq_valid}}"
    ),
    45: (
        "select transaction_country as country, sum(revenue) as revenue "
        "from mart.fct_sm_sales where {{dq_valid}} group by 1 order by 2 desc"
    ),
    46: (
        "select transaction_date, sum(revenue) as revenue "
        "from mart.fct_sm_sales where {{dq_valid}} group by 1 order by 1"
    ),
    # 47-50: the fact table is referenced by its real name, not an alias, so the
    # fully qualified reference the field filter emits resolves.
    47: (
        "select p.product_name, sum(mart.fct_sm_sales.volume) as volume "
        "from mart.fct_sm_sales "
        "join mart.dim_sm_product p using (product_id) "
        "where {{dq_valid}} group by 1 order by 2 desc"
    ),
    48: (
        "select p.product_group, sum(mart.fct_sm_sales.margin) as margin "
        "from mart.fct_sm_sales "
        "join mart.dim_sm_product p using (product_id) "
        "where {{dq_valid}} group by 1 order by 2 desc"
    ),
    49: (
        "select c.customer_name, sum(mart.fct_sm_sales.revenue) as revenue "
        "from mart.fct_sm_sales "
        "join mart.dim_sm_customer c using (customer_id) "
        "where {{dq_valid}} group by 1 order by 2 desc"
    ),
    50: (
        "select c.segment, sum(mart.fct_sm_sales.revenue) as revenue "
        "from mart.fct_sm_sales "
        "join mart.dim_sm_customer c using (customer_id) "
        "where {{dq_valid}} group by 1 order by 2 desc"
    ),
}


def api(path: str, method: str = "GET", body: dict | None = None) -> dict | list:
    key = os.environ.get("METABASE_API_KEY")
    if not key:
        sys.exit("METABASE_API_KEY is not set.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}/api{path}",
        data=data,
        method=method,
        headers={"x-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        sys.exit(f"{method} {path} failed: {exc.code} {exc.read()[:500]!r}")


def find_dq_valid_field() -> int:
    """Locate mart.fct_sm_sales.dq_valid in the synced metadata."""
    # /api/database returns {"data": [...]} on Metabase 0.5x, a bare list on older builds.
    databases = api("/database")
    if isinstance(databases, dict):
        databases = databases.get("data", [])
    for db in databases:
        if db.get("engine") != "postgres":
            continue
        meta = api(f"/database/{db['id']}/metadata")
        for table in meta.get("tables", []):
            if table.get("schema") == "mart" and table.get("name") == "fct_sm_sales":
                for field in table.get("fields", []):
                    if field.get("name") == "dq_valid":
                        return field["id"]
                sys.exit(
                    "mart.fct_sm_sales is synced but has no dq_valid column.\n"
                    "Rebuild the dbt models, then re-sync the database schema in "
                    "Metabase (Admin > Databases > Sync database schema)."
                )
    sys.exit("Could not find mart.fct_sm_sales in any synced Postgres database.")


def template_tags(field_id: int) -> dict:
    # No card-level default on purpose. A default here would reassert itself
    # whenever the dashboard filter is cleared, making "show every row"
    # impossible. The default lives on the dashboard parameter instead.
    return {
        TAG_NAME: {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sm-dq-{TAG_NAME}")),
            "name": TAG_NAME,
            "display-name": PARAM_NAME,
            "type": "dimension",
            "dimension": ["field", field_id, None],
            "widget-type": PARAM_TYPE,
            "required": False,
        }
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--revert", metavar="BACKUP_JSON")
    args = ap.parse_args()

    if args.revert:
        backup = json.load(open(args.revert))
        for cid, card in backup["cards"].items():
            api(f"/card/{cid}", "PUT", {"dataset_query": card["dataset_query"]})
            print(f"reverted card {cid}")
        api(
            f"/dashboard/{DASHBOARD_ID}",
            "PUT",
            {
                "parameters": backup["dashboard"]["parameters"],
                "dashcards": backup["dashboard"]["dashcards"],
            },
        )
        print("reverted dashboard")
        return

    field_id = find_dq_valid_field()
    print(f"mart.fct_sm_sales.dq_valid -> field id {field_id}")

    dashboard = api(f"/dashboard/{DASHBOARD_ID}")
    cards = {cid: api(f"/card/{cid}") for cid in CARD_SQL}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = f"backup_dashboard{DASHBOARD_ID}_{stamp}.json"
    with open(backup_path, "w") as fh:
        json.dump({"dashboard": dashboard, "cards": cards}, fh, indent=1)
    print(f"backup written to {backup_path}")

    if args.dry_run:
        for cid, sql in CARD_SQL.items():
            old = cards[cid]["dataset_query"]["stages"][0].get("native")
            print(f"\n--- card {cid}: {cards[cid]['name']}")
            print(f"  before: {old}")
            print(f"  after : {sql}")
        unwired = [
            c["card"]["id"]
            for c in dashboard["dashcards"]
            if (c.get("card") or {}).get("id") and c["card"]["id"] not in CARD_SQL
        ]
        print(f"\nleft unwired (data quality cards): {sorted(unwired)}")
        print(f"dashboard parameter to add: {PARAM_NAME} ({PARAM_TYPE}), default true")
        print("\nDry run only. Nothing was changed.")
        return

    tags = template_tags(field_id)
    for cid, sql in CARD_SQL.items():
        query = json.loads(json.dumps(cards[cid]["dataset_query"]))
        query["stages"][0]["native"] = sql
        query["stages"][0]["template-tags"] = tags
        api(f"/card/{cid}", "PUT", {"dataset_query": query})
        print(f"updated card {cid}: {cards[cid]['name']}")

    parameters = [p for p in dashboard.get("parameters", []) if p.get("slug") != PARAM_SLUG]
    parameters.append(
        {
            "id": PARAM_ID,
            "name": PARAM_NAME,
            "slug": PARAM_SLUG,
            "type": PARAM_TYPE,
            "sectionId": "boolean",
            "default": [True],
        }
    )

    dashcards = json.loads(json.dumps(dashboard["dashcards"]))
    for dc in dashcards:
        cid = (dc.get("card") or {}).get("id")
        if cid not in CARD_SQL:
            continue
        mappings = [m for m in (dc.get("parameter_mappings") or []) if m.get("parameter_id") != PARAM_ID]
        mappings.append(
            {
                "parameter_id": PARAM_ID,
                "card_id": cid,
                "target": ["dimension", ["template-tag", TAG_NAME], {"stage-number": 0}],
            }
        )
        dc["parameter_mappings"] = mappings

    api(
        f"/dashboard/{DASHBOARD_ID}",
        "PUT",
        {"parameters": parameters, "dashcards": dashcards},
    )
    print(f"dashboard {DASHBOARD_ID} updated: filter added and wired to {len(CARD_SQL)} cards")
    print(f"to undo: python {os.path.basename(__file__)} --revert {backup_path}")


if __name__ == "__main__":
    main()
