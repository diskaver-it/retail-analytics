"""Load the landed parquet into DuckDB.

This is the seam between EL and T: above it, Python moves bytes; below it,
everything is SQL in dbt. `raw.transactions` is a straight copy of landing with
the source sheet tacked on, so when a mart looks wrong there is always something
untransformed to check it against.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from . import config

RAW_TABLE = "raw.transactions"


def connect(warehouse: Path = config.WAREHOUSE, read_only: bool = False):
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(warehouse), read_only=read_only)


def load_raw(landing_dir: Path = config.LANDING_DIR,
             warehouse: Path = config.WAREHOUSE) -> int:
    """Rebuild raw.transactions from every parquet in landing. Returns row count."""
    files = sorted(landing_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"nothing to load - {landing_dir} has no parquet files")

    columns = ", ".join(config.COLUMNS)
    with connect(warehouse) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {RAW_TABLE} AS
            SELECT {columns}, parse_filename(filename, true) AS source_sheet
            FROM read_parquet($files, filename = true)
            """,
            {"files": [str(f) for f in files]},
        )
        return con.execute(f"SELECT count(*) FROM {RAW_TABLE}").fetchone()[0]


def profile(warehouse: Path = config.WAREHOUSE) -> dict:
    """Headline numbers, printed after a load so a bad run is obvious immediately."""
    with connect(warehouse, read_only=True) as con:
        row = con.execute(
            f"""
            SELECT
                count(*)                                        AS rows,
                count(DISTINCT invoice_no)                      AS invoices,
                count(DISTINCT customer_id)                     AS customers,
                count(DISTINCT stock_code)                      AS products,
                min(invoice_ts)::DATE                           AS first_day,
                max(invoice_ts)::DATE                           AS last_day,
                sum(customer_id IS NULL)                        AS rows_without_customer,
                sum(starts_with(invoice_no, 'C')::INT)          AS cancellation_rows,
                sum((quantity < 0)::INT)                        AS negative_quantity_rows
            FROM {RAW_TABLE}
            """
        ).fetchone()
        names = [d[0] for d in con.description]
    return dict(zip(names, row))
