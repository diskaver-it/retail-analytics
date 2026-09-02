"""Build a fake raw.transactions that has the same shape of problem as the real one.

CI cannot download 45 MB from a university archive on every push, and a dbt
project nobody builds is a folder of untested SQL. So the models get built in CI
against this instead: a few thousand rows carrying every awkward case the real
extract has - guests, returns, postage lines, duplicate rows, free samples - so
that the tests in _marts.yml are actually exercised rather than passing on an
empty table.

The numbers here are invented. Nothing in the README or the dashboard is measured
from it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config

# Codes the shop uses for its own bookkeeping. fct_order_lines drops these, and
# they need to exist in the fixture or the test that checks it never fires.
ADMIN_CODES = ["POST", "DOT", "BANK CHARGES", "ADJUST", "M"]

PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("71053", "WHITE METAL LANTERN", 3.39),
    ("22633", "HAND WARMER UNION JACK", 1.85),
    ("47566", "PARTY BUNTING", 4.95),
    ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("22423", "REGENCY CAKESTAND 3 TIER", 12.75),
]

COUNTRIES = ["United Kingdom", "France", "Germany", "EIRE", "Netherlands"]


def transactions(n_customers: int = 300, months: int = 24, seed: int = 7) -> pd.DataFrame:
    """Generate invoice lines spread over `months`, starting 2009-12-01."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2009-12-01")

    rows = []
    invoice_counter = 500000

    # Each customer joins in some month and then comes back a decaying number of
    # times, which is what makes the cohort mart produce a triangle rather than a
    # diagonal line.
    for customer in range(1, n_customers + 1):
        customer_id = 12000 + customer
        cohort = int(rng.integers(0, months))
        country = COUNTRIES[int(rng.integers(0, len(COUNTRIES)))]
        n_orders = 1 + int(rng.geometric(0.45)) - 1

        offsets = sorted({cohort} | {
            min(cohort + int(rng.integers(1, months)), months - 1)
            for _ in range(n_orders)
        })

        for offset in offsets:
            invoice_counter += 1
            invoice_no = str(invoice_counter)
            day = int(rng.integers(1, 28))
            hour = int(rng.integers(8, 18))
            ts = start + pd.DateOffset(months=offset) + pd.Timedelta(days=day - 1, hours=hour)

            for _ in range(1 + int(rng.integers(0, 4))):
                code, description, price = PRODUCTS[int(rng.integers(0, len(PRODUCTS)))]
                quantity = int(rng.integers(1, 25))
                rows.append((invoice_no, code, description, quantity, ts, price,
                             float(customer_id), country))

            # Postage rides along on roughly a third of orders.
            if rng.random() < 0.3:
                rows.append((invoice_no, ADMIN_CODES[int(rng.integers(0, len(ADMIN_CODES)))],
                             "POSTAGE", 1, ts, 18.0, float(customer_id), country))

    df = pd.DataFrame(rows, columns=list(config.COLUMNS))

    df = pd.concat([df, _guest_lines(df, rng), _cancellations(df, rng)], ignore_index=True)
    df = pd.concat([df, df.sample(frac=0.005, random_state=seed)], ignore_index=True)  # exact dupes

    # A few giveaways at zero price - the real file has plenty.
    free = df.sample(frac=0.004, random_state=seed + 1).copy()
    free["unit_price"] = 0.0
    df = pd.concat([df, free], ignore_index=True)

    df = df.sort_values("invoice_ts").reset_index(drop=True)
    df["invoice_ts"] = pd.to_datetime(df["invoice_ts"])
    return df


def _guest_lines(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Copy a fifth of the lines onto new invoices with no customer id."""
    guests = df.sample(frac=0.2, random_state=int(rng.integers(0, 10**6))).copy()
    guests["invoice_no"] = ["9" + str(900000 + i) for i in range(len(guests))]
    guests["customer_id"] = np.nan
    return guests


def _cancellations(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Return a slice of the orders: C-prefixed invoice, negative quantity."""
    returns = df[df["customer_id"].notna()].sample(
        frac=0.03, random_state=int(rng.integers(0, 10**6))
    ).copy()
    returns["invoice_no"] = "C" + returns["invoice_no"]
    returns["quantity"] = -returns["quantity"]
    returns["invoice_ts"] = returns["invoice_ts"] + pd.Timedelta(days=5)
    return returns


def build_warehouse(warehouse: Path, seed: int = 7) -> int:
    """Drop a synthetic raw.transactions into a DuckDB file. Returns row count."""
    from . import warehouse as wh

    df = transactions(seed=seed)
    df = df.assign(source_sheet="synthetic")

    with wh.connect(warehouse) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.register("synthetic_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {wh.RAW_TABLE} AS SELECT * FROM synthetic_df")
        return con.execute(f"SELECT count(*) FROM {wh.RAW_TABLE}").fetchone()[0]
