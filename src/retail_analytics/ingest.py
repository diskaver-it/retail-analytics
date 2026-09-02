"""Fetch the source workbook and land it as parquet, one file per sheet.

Nothing is cleaned or filtered here. Cancellations, missing customer ids and
negative quantities all survive into landing untouched - they are real events,
and deciding what to do with them belongs in staging where the decision is
visible as SQL. If ingest quietly drops rows you can never tell afterwards
whether a number came out small because the business is small or because ingest
ate it.

The workbook never exists as a whole object in this process. Three shorter
implementations were tried first - pandas with openpyxl, pandas with calamine,
and DuckDB's read_xlsx - and all three died with MemoryError on a laptop with a
browser open, because each of them materialises a full sheet (over half a million
rows) before handing anything back. Reading row by row and writing a row group at
a time is slower and it finishes.
"""
from __future__ import annotations

import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

from . import config

# UCI returns 403 to the default urllib user agent.
USER_AGENT = "Mozilla/5.0"

BATCH_ROWS = 50_000

LANDING_SCHEMA = pa.schema([
    ("invoice_no", pa.string()),
    ("stock_code", pa.string()),
    ("description", pa.string()),
    ("quantity", pa.int64()),
    ("invoice_ts", pa.timestamp("us")),
    ("unit_price", pa.float64()),
    ("customer_id", pa.float64()),
    ("country", pa.string()),
])


def download(url: str = config.SOURCE_URL,
             destination: Path = config.ARCHIVE,
             force: bool = False) -> Path:
    """Fetch the zip once and keep it. Returns the local path.

    Streamed to a .part file and renamed at the end, so an interrupted run cannot
    leave a truncated archive sitting there looking finished.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return destination

    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as sink:
        shutil.copyfileobj(response, sink, length=1 << 20)

    partial.replace(destination)
    return destination


def extract_workbook(archive: Path = config.ARCHIVE, into: Path | None = None) -> Path:
    """Unpack the .xlsx out of the zip and onto disk."""
    into = into or archive.parent
    with zipfile.ZipFile(archive) as bundle:
        name = next(n for n in bundle.namelist() if n.endswith(".xlsx"))
        target = into / Path(name).name
        if not target.exists():
            with bundle.open(name) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink, length=1 << 20)
    return target


def stream_sheet(workbook: Path, sheet: str, destination: Path,
                 batch_rows: int = BATCH_ROWS) -> int:
    """Copy one sheet into a parquet file. Returns the number of rows written."""
    book = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    try:
        rows = book[sheet].iter_rows(values_only=True)
        _check_header(next(rows), sheet)

        written = 0
        batch: list[tuple] = []
        with pq.ParquetWriter(destination, LANDING_SCHEMA) as writer:
            for row in rows:
                if row[0] is None:      # openpyxl pads the used range with blanks
                    continue
                batch.append(row)
                if len(batch) >= batch_rows:
                    writer.write_table(_to_table(batch))
                    written += len(batch)
                    batch.clear()
            if batch:
                writer.write_table(_to_table(batch))
                written += len(batch)
        return written
    finally:
        book.close()


def _check_header(header: tuple, sheet: str) -> None:
    seen = [str(cell).strip() if cell is not None else "" for cell in header]
    missing = [c for c in config.COLUMN_RENAMES if c not in seen]
    if missing:
        raise ValueError(f"sheet {sheet!r} is missing columns: {missing}")


def _to_table(batch: list[tuple]) -> pa.Table:
    columns = list(zip(*batch))
    return pa.Table.from_arrays(
        [
            pa.array([_as_text(v) for v in columns[0]], type=pa.string()),
            pa.array([_as_text(v) for v in columns[1]], type=pa.string()),
            pa.array([_as_text(v) for v in columns[2]], type=pa.string()),
            pa.array([_as_int(v) for v in columns[3]], type=pa.int64()),
            pa.array(columns[4], type=pa.timestamp("us")),
            pa.array([_as_float(v) for v in columns[5]], type=pa.float64()),
            pa.array([_as_float(v) for v in columns[6]], type=pa.float64()),
            pa.array([_as_text(v) for v in columns[7]], type=pa.string()),
        ],
        schema=LANDING_SCHEMA,
    )


def _as_text(value) -> str | None:
    """Excel hands back invoice and stock codes as numbers when they look numeric.

    Without the integer check, invoice 536365 lands as the string '536365.0' and
    stops joining to the cancellation 'C536365' - which is exactly the kind of bug
    that shows up three models downstream as a return rate of zero.
    """
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _as_int(value) -> int | None:
    return None if value is None else int(value)


def _as_float(value) -> float | None:
    return None if value is None else float(value)


def _slug(sheet: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", sheet.lower()).strip("_")


def write_landing(workbook: Path, landing_dir: Path = config.LANDING_DIR) -> list[Path]:
    """Stream every sheet in config.SHEETS to its own parquet file."""
    landing_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for sheet in config.SHEETS:
        path = landing_dir / f"{_slug(sheet)}.parquet"
        stream_sheet(workbook, sheet, path)
        written.append(path)
    return written


def run(landing_dir: Path = config.LANDING_DIR, force_download: bool = False) -> list[Path]:
    """Download, unpack, land. Skips the parse if landing is already populated."""
    archive = download(force=force_download)

    expected = [landing_dir / f"{_slug(s)}.parquet" for s in config.SHEETS]
    if all(p.exists() for p in expected) and not force_download:
        return expected

    return write_landing(extract_workbook(archive), landing_dir=landing_dir)
