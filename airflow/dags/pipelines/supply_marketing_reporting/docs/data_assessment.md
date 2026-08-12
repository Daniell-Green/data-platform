# Data Assessment — Supply & Marketing Reporting

Source files: `sales.csv`, `Customers.xlsx`, `Products.xlsx`, `Margin.xlsx`
(12 sales transactions, 8 customers, 5 product rows / 4 distinct products, 4 margin rows).

## Identified data quality issues

| # | File | Issue | Example |
|---|---|---|---|
| 1 | sales.csv | Missing `CustomerID` | Transaction 1009 |
| 2 | sales.csv | `ProductID` not present in `Products`/`Margin` (orphan foreign key) | Transaction 1010 → `P999` |
| 3 | sales.csv | Negative `Quantity` with no accompanying transaction type/reference to the original booking | Transaction 1012 → `-10` |
| 4 | sales.csv | Two transactions identical in every column except `TransactionID` | Transactions 1007 / 1008 |
| 5 | Products.xlsx | Duplicate `ProductID` with two different names — a broken dimension key | `P300` → "Jet A1" and "Jet A-1" |
| 6 | Customers.xlsx | Two distinct, validly-keyed customers with near-identical names | `C007` "Jet Fuels GmbH", `C008` "Jet Fuel GmbH" |
| 7 | sales.csv | `;`-delimited file, German date format (`DD.MM.YYYY`) | whole file |

## Assumptions made

- The source files are treated as the authoritative, current state of the business systems (per the brief) — no external system was consulted to resolve ambiguities.
- `TransactionID` is assumed to originate from the source system (e.g. SAP), not generated at ingestion. This is why issue #4 is **not** treated as a hard duplicate: two different source-assigned IDs are the strongest signal available, and there's no process/document number in the data to say otherwise.
- Issue #5 (duplicate `ProductID`) is treated differently from #6 (similar customer names) because #5 is a **broken key**, not a business ambiguity: `ProductID` must be unique for `sales` to join to `Products` without silently duplicating (fanning out) transaction rows. #6 involves two valid, unique `CustomerID`s — nothing is technically broken, so it's a business/MDM question, not a forced technical fix.
- Issue #3 (negative quantity) is assumed to represent an unresolved data quality problem rather than a confirmed return/cancellation, since the source data has no transaction-type column to distinguish a sale from a reversal. Treating it as a confirmed return would be asserting business meaning the data doesn't actually support.

## Risks discovered

- **Silent revenue misstatement**: naively summing `Quantity * UnitPrice` over the raw file would both overstate revenue (orphan/unknown-customer rows included with no way to attribute them) and understate confidence (the negative-quantity row nets against other revenue without any visibility that it's unverified).
- **Row multiplication on join**: joining `sales` to `Products` on the raw, non-deduplicated `Products` table would double-count every `P300` transaction if not fixed before the fact table is built.
- **Customer master ambiguity**: if `C007`/`C008` are actually the same legal entity, "Top Customers" and any customer-level revenue KPI will be split across two rows, understating each one's true rank. If they're genuinely different entities, an automatic merge would be a worse error (misattributing revenue).
- **No independent volume/value validation possible** from this data alone — there's no source system reconciliation point (e.g. an invoice total) to check the transaction file against.

## Recommended remediation actions

1. **Don't correct data on the way in.** Land source files into `raw` unmodified — corrections belong in a traceable, reviewable transformation step (`staging`), not silently in ingestion.
2. **Flag, don't drop, at the row level.** `staging.stg_sm_sales` carries every raw row forward plus `dq_valid` (boolean) and `dq_issues` (list of reason codes) computed explicitly in SQL, so invalid rows are visible, auditable, and countable — not silently vanished.
3. **Fix broken keys before they can fan out joins.** `staging` deduplicates `ProductID` deterministically (documented survivorship rule — see `data_model.md`), since this is a structural fix, not a business judgment call.
4. **Surface business ambiguities instead of resolving them speculatively.** The `C007`/`C008` near-duplicate is flagged (`possible_duplicate_customer`) and left for the business to confirm — an analytics pipeline shouldn't unilaterally merge master data.
5. **Exclude `dq_valid = false` rows from headline KPI marts**, but make them fully visible in a dedicated Data Quality mart/dashboard view (row count, $ value at risk, % of total) — matching the brief's explicit "Data quality view" requirement.
6. **Push these issues back upstream.** All of this is a downstream mitigation, not a fix. The real remediation is: enforce `NOT NULL CustomerID` and FK integrity at the source (SAP) or the earliest ingestion point, and dedupe the product master at its source of truth.
