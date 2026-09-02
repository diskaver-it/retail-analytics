"""Paths and source constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw"
LANDING_DIR = ROOT / "data" / "landing"
WAREHOUSE = ROOT / "data" / "retail.duckdb"

SOURCE_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
ARCHIVE = RAW_DIR / "online_retail_ii.zip"

# The workbook holds one sheet per year with identical columns. They land as two
# parquet files and get unioned in staging, so the year a row came from stays
# visible if one of them turns out to be broken.
SHEETS = ("Year 2009-2010", "Year 2010-2011")

# Source headers are inconsistent - 'Customer ID' has a space in it, the rest are
# CamelCase. Renaming at the door means no SQL model downstream has to quote a
# column name.
COLUMN_RENAMES = {
    "Invoice": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_ts",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}

COLUMNS = tuple(COLUMN_RENAMES.values())
