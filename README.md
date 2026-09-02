# retail-analytics

A warehouse and a set of analytics models over the UCI **Online Retail II** extract:
1,067,371 invoice lines from a UK online gift wholesaler, December 2009 to December 2011.

The pipeline is `download → land → warehouse → dbt → marts → dashboard`. Python moves bytes as
far as `raw.transactions`; everything after that is SQL, and the dashboard is markdown.

```
ingest (python)        transform (dbt)         marts                    dashboard (evidence)
──────────────────     ─────────────────       ────────────────────     ────────────────────
UCI .xlsx              stg_transactions        fct_order_lines          Trading overview
 → parquet landing      (typed + flagged,      dim_customer             Customers
 → raw.transactions      nothing removed)      dim_product              What was removed
                                               dim_date
                                               mart_monthly_revenue
                                               mart_cohort_retention
                                               mart_rfm
```

**54 dbt checks and 25 Python tests, all green.** The dbt models are built in CI against a
synthetic warehouse, so every model and every test runs on each push without downloading
45 MB from a university server.

## What the data turned out to be

As loaded, before any modelling:

| | |
|---|---|
| Rows landed | 1,067,371 |
| Invoices | 53,628 |
| Distinct customer ids | 5,942 |
| Distinct stock codes | 5,304 |
| Window | 2009-12-01 → 2011-12-09 |

After the models, which is a different population — bookkeeping lines and duplicates are gone,
and a customer needs at least one purchase to get a row:

| | |
|---|---|
| Order lines | 1,027,054 |
| Orders (excluding cancellations) | 44,715 |
| Customers with a purchase | 5,853 |
| Net revenue | £18,925,714 |
| Repeat customers | 72.3% |

## Five decisions worth arguing about

### 1. Staging flags, it does not filter

`stg_transactions` returns exactly as many rows as the source, and a dbt test
([assert_staging_drops_nothing.sql](transform/tests/assert_staging_drops_nothing.sql))
fails the build if that ever stops being true. Cancellations, guest baskets, postage lines
and duplicate rows all arrive as boolean columns instead of disappearing into somebody's
`WHERE` clause.

The reason is that filtering early is unfalsifiable. Once a row is gone you cannot tell
whether a total is small because the business is small or because ingest ate it. As columns,
each mart states out loud which rows it wanted, and every number reconciles back to raw.

### 2. Guest baskets stay in revenue and stay out of retention

243,007 lines (22.8%) have no customer id, and they carry **£2,567,652 — 13.6% of net
revenue**. The common shortcut is `WHERE customer_id IS NOT NULL` at the top of the analysis,
which deletes an eighth of the revenue before anyone asks a question.

So the denominators are deliberately different: revenue is measured over every line,
retention only over customers who can be followed across time. `dim_customer` cannot contain
guests — with no id there is no way to know whether two guest baskets are one person twice or
two people once.

### 3. Postage is not a product

62 stock codes are the shop's own bookkeeping — `POST`, `DOT`, `BANK CHARGES`, `AMAZONFEE`,
`ADJUST`, `M` for manual. 6,093 lines, worth **−£95,225** net. They move money but nobody
ordered them, and a "top products" chart that keeps them ranks postage first.

The rule is a shape, not a hand-written list: a real code is five digits with an optional
letter suffix (`85123A`, `22633`). Alongside them, **34,337 rows (3.2%)** are byte-identical
duplicates. Both are removed once, in `fct_order_lines`, and nowhere else.

### 4. The last month is a cliff, and the model says so

The extract stops on 9 December 2011. December therefore shows **−69.1% MoM and a 28.3%
return rate** — returns of November's orders land in December while December's own orders
mostly do not exist yet. Nothing is wrong; the file just ends.

`mart_monthly_revenue.is_partial_month` marks it so the dashboard can mask it. The same idea
runs through `mart_cohort_retention.months_observable`: the cohort that first bought last month
has had no chance to return, and without that column a chart plots its 0% next to a 2009
cohort's real 0% as if they meant the same thing.

### 5. Recency is measured against the data, not against today

`mart_rfm` scores recency from the last day in the extract. Against `current_date` every
customer in a 2011 file is equally, uselessly stale, all five quintiles collapse into one and
the segmentation says nothing. Anything that hard-codes "now" breaks the same way the moment
the data stops being live.

The 5×5 cutoffs are the usual convention rather than something derived from this business —
stated as such in the model, because a segmentation presented as fact is worse than one
presented as a starting point.

## A finding the tests turned up

The first build against real data failed: 87 fact rows had a `customer_id` with no matching
row in `dim_customer`.

It was not a bug. **23 customers appear only as returns** — 87 lines, −£1,406, the earliest on
the very first day of the file. They bought *before* 2009-12-01, outside the window, and sent
something back inside it. With no purchase they have no cohort, so they correctly have no row
in `dim_customer`.

The relationship test is now scoped to purchase lines, and the explanation is pinned by its own
test ([assert_missing_customers_only_ever_returned.sql](transform/tests/assert_missing_customers_only_ever_returned.sql)):
the day a customer goes missing from `dim_customer` with a genuine purchase attached, the build
fails instead of the shortfall spreading quietly through every customer-level metric.

## Reading the marts

Concentration is severe, which is what a wholesaler looks like: **1,476 customers (25%) are
"Champions" and account for 70.2% of revenue.** Retention does not decay the way a consumer
product's does — the December 2009 cohort sits between 33% and 42% monthly for half a year,
and month 3 (42.5%) is higher than month 1 (35.0%), which is seasonal reordering rather than
a leak.

## The dashboard

Three pages, built with [Evidence](https://evidence.dev) — the whole dashboard is markdown and
SQL in `dashboard/`, so it diffs and reviews like the rest of the repo rather than sitting in a
binary nobody can open.

- **Trading overview** — headline figures, revenue by month, and the split between money that can
  be tied to a customer and money that cannot.
- **Customers** — cohort retention and RFM segments, with the caveats on the page rather than in
  a footnote.
- **What was removed** — the rows the pipeline dropped and the argument for dropping them.

The third page is the unusual one. It is there because every figure on the other two depends on
it: a reader who cannot see what was thrown away has no way to judge what is left.

GitHub Actions rebuilds the warehouse, runs `dbt build`, builds the site and publishes it to
Pages on every push to `main`.

## Running it

```bash
pip install -e ".[dev]" "dbt-duckdb>=1.9"
```

Pull the data and build the warehouse — about 45 MB from UCI, then a few minutes of parsing:

```bash
python -m retail_analytics all
```

Then the models:

```bash
cd transform && DBT_PROFILES_DIR=. dbt deps && DBT_PROFILES_DIR=. dbt build
```

And the dashboard, which reads the warehouse the models just built:

```bash
cd dashboard && npm install && npm run sources && npm run dev
```

It comes up on <http://localhost:3000/retail-analytics> — the base path is set for GitHub Pages
and applies in dev too.

Tests, offline, no data needed:

```bash
pytest
```

To build the models without downloading anything — this is what CI does:

```bash
python -m retail_analytics synthetic --warehouse data/ci.duckdb
```

### Notes

- `profiles.yml` lives in `transform/` rather than `~/.dbt` so a clone runs without setup.
  There is nothing secret in it; DuckDB is a file. Point it elsewhere with `RETAIL_DUCKDB`.
- On Windows, `dbt.exe` installs outside `PATH`; call it by full path or use
  `python -m dbt.cli.main`.
- The workbook is never held in memory as a whole object. Three shorter implementations were
  tried first — pandas with openpyxl, pandas with calamine, and DuckDB's `read_xlsx` — and all
  three died with `MemoryError`, because each materialises a full sheet (over half a million
  rows) before returning anything. `ingest.py` reads row by row and writes a parquet row group
  at a time: slower, and it finishes.
- `evidence build` wants more than 1.5 GB of Node heap. That is why the production build runs in
  CI and `npm run dev` is the local loop; if you do want to build locally, raise the limit with
  `NODE_OPTIONS=--max-old-space-size=4096`.

## Source

Chen, D. (2019). *Online Retail II*. UCI Machine Learning Repository.
<https://archive.ics.uci.edu/dataset/502/online+retail+ii>
