# Dashboard — Supply & Marketing Reporting

**Metabase:** https://metabase.franklingreen.de/dashboard/3
Collection: *Supply & Marketing Reporting*

Metabase reads through the `metabase_ro` role, which has SELECT on `mart` only.
The BI layer cannot reach `raw` or `staging`, so every figure on the dashboard
comes from the modelled marts rather than from ad-hoc queries against source data.

## Layout

| Section | Cards |
|---|---|
| Executive Summary | Total Revenue · Total Volume · Total Margin · Margin % · Revenue Excluded by Data Quality |
| Revenue Analysis | Revenue by Country (bar) · Revenue Trend (line) |
| Product Performance | Volume by Product (bar) · Margin by Product Group (bar) |
| Customer Overview | Top Customers by Revenue (row) · Revenue by Customer Segment (bar) |
| Data Quality | Flagged Records by Issue · Flagged Records (row-level detail) |

## The data quality filter

`fct_sm_sales` holds **every** source transaction, including rows that failed a
quality rule. The dashboard, not the model, decides which of them count.

A single dashboard filter — **Data quality**, a boolean field filter on
`fct_sm_sales.dq_valid` — is wired to all ten cards that read the fact. It
**defaults to `true`**, so the dashboard opens showing exactly the figures below.
Clearing it includes the flagged rows: revenue rises, and the unattributable
transactions appear under "Unknown Customer" and "Unknown Product" in the
dimensional breakdowns rather than vanishing from them.

The three Data Quality cards (Revenue Excluded, Flagged Records, Flagged Records
by Issue) read `mart_sm_data_quality` and are deliberately **not** wired to the
filter — they must always show the flagged rows, whatever the rest of the
dashboard is displaying.

Because every card is a native SQL question, the filter is implemented as a
Metabase field-filter template tag (`{{dq_valid}}`) in each card's SQL rather
than an automatic column mapping. A card that is not wired silently ignores the
filter and reports on all rows, so the wiring is per-card and worth re-checking
when a card is added.

## Design choices

**The quality filter is a visible control, not a hidden predicate.** Previously
the fact table itself dropped flagged rows, so a reader had no way to tell that
the headline revenue was a subset, and no way to see the full picture without
writing SQL. Moving the decision into a dashboard control keeps the default
figures identical while making the exclusion auditable and reversible by the
reader.

**The excluded-revenue KPI sits in the executive summary, not buried in the data
quality section.** A reader who never scrolls still sees that 26,800 EUR of
source data is not represented in the headline figures. Putting it beside the
revenue number makes the caveat as prominent as the claim.

**Form follows the question.** Single headline values are scalars, not
single-bar charts. Magnitude comparisons across categories are bars. Change over
time is a line. Row-level quality detail is a table, because the reader needs to
identify specific transactions rather than compare quantities.

**Top Customers is a row chart**, not a column chart: customer names are long,
and horizontal bars keep them readable without rotated labels.

**No dual-axis charts.** Revenue and margin are different scales and appear in
separate cards rather than sharing one plot with two y-axes, which is
consistently misread.

**Each card carries a single series**, so identity never depends on colour and no
legend is needed — the card title names the measure.

## Figures as built

With the Data quality filter at its default (`dq_valid = true`):

| KPI | Value |
|---|---|
| Total Revenue | 501,500 EUR |
| Total Volume | 1,100 |
| Total Margin | 18,000 EUR |
| Margin % | 3.6% |
| Revenue excluded by data quality | 26,800 EUR |

Revenue by country: DE 361,600 · AT 62,400 · PL 46,500 · CZ 31,000.

## Reading the dashboard honestly

Two things a presenter should raise before being asked:

**Aral AG leads the customer ranking on 180,000 EUR, entirely from transactions
1007 and 1008** — the pair flagged as possible duplicates. That single unresolved
question decides the top customer. It is visible in the Data Quality section
rather than hidden.

**Margin % is low (3.6%) because margin is a flat per-unit figure** applied
across products with very different unit prices. It is a reported measure, not a
commercial assessment, and would need validation with the business before anyone
acts on it.
