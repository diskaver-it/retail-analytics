import openpyxl
import pandas as pd
import pytest

from conftest import sample_frame
from retail_analytics import config, ingest

SHEET = config.SHEETS[0]


def make_workbook(path, frame=None, headers=None):
    """Write a real .xlsx with the source's own column names."""
    frame = sample_frame() if frame is None else frame
    headers = headers or list(config.COLUMN_RENAMES)

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = SHEET
    sheet.append(headers)
    for row in frame.itertuples(index=False):
        sheet.append([None if pd.isna(v) else v for v in row])
    book.save(path)
    return path


def test_stream_sheet_round_trips_the_data(tmp_path):
    workbook = make_workbook(tmp_path / "book.xlsx")
    landed = tmp_path / "sheet.parquet"

    rows = ingest.stream_sheet(workbook, SHEET, landed)
    result = pd.read_parquet(landed)

    assert rows == len(sample_frame())
    assert list(result.columns) == list(config.COLUMNS)
    assert result["quantity"].tolist() == sample_frame()["quantity"].tolist()
    assert result["customer_id"].isna().sum() == 1


def test_stream_sheet_rejects_a_sheet_with_a_missing_column(tmp_path):
    headers = [h for h in config.COLUMN_RENAMES if h != "Customer ID"]
    frame = sample_frame().drop(columns=["customer_id"])
    workbook = make_workbook(tmp_path / "broken.xlsx", frame=frame, headers=headers)

    with pytest.raises(ValueError, match="Customer ID"):
        ingest.stream_sheet(workbook, SHEET, tmp_path / "out.parquet")


def test_batching_does_not_change_the_result(tmp_path):
    workbook = make_workbook(tmp_path / "book.xlsx")

    one_go = tmp_path / "whole.parquet"
    in_pieces = tmp_path / "batched.parquet"
    ingest.stream_sheet(workbook, SHEET, one_go, batch_rows=1000)
    ingest.stream_sheet(workbook, SHEET, in_pieces, batch_rows=2)

    pd.testing.assert_frame_equal(pd.read_parquet(one_go), pd.read_parquet(in_pieces))


@pytest.mark.parametrize(
    "value, expected",
    [
        (536365.0, "536365"),      # Excel hands numeric-looking invoices back as floats
        (536365, "536365"),
        ("C536379", "C536379"),
        ("85123A", "85123A"),
        ("  padded  ", "padded"),
        (None, None),
        ("", None),
    ],
)
def test_as_text_does_not_invent_a_decimal_point(value, expected):
    assert ingest._as_text(value) == expected


@pytest.mark.parametrize(
    "sheet, expected",
    [("Year 2009-2010", "year_2009_2010"), ("Year 2010-2011", "year_2010_2011")],
)
def test_slug(sheet, expected):
    assert ingest._slug(sheet) == expected


def test_extract_workbook_unpacks_the_xlsx_once(tmp_path):
    workbook = make_workbook(tmp_path / "book.xlsx")
    archive = tmp_path / "bundle.zip"
    with __import__("zipfile").ZipFile(archive, "w") as bundle:
        bundle.write(workbook, arcname="online_retail_II.xlsx")

    out = tmp_path / "unpacked"
    out.mkdir()
    first = ingest.extract_workbook(archive, into=out)
    stamp = first.stat().st_mtime_ns
    second = ingest.extract_workbook(archive, into=out)

    assert first == second
    assert second.stat().st_mtime_ns == stamp, "extracted the workbook a second time"


def test_download_reuses_the_cached_archive(tmp_path, monkeypatch):
    cached = tmp_path / "online_retail_ii.zip"
    cached.write_bytes(b"not really a zip")

    def explode(*args, **kwargs):
        raise AssertionError("download() went to the network with a cached file present")

    monkeypatch.setattr(ingest.urllib.request, "urlopen", explode)
    assert ingest.download(destination=cached) == cached


def test_run_skips_the_parse_when_landing_is_already_there(landing_dir, monkeypatch):
    monkeypatch.setattr(ingest, "download", lambda force=False: landing_dir / "archive.zip")

    def explode(*args, **kwargs):
        raise AssertionError("run() re-parsed the workbook instead of reusing landing")

    monkeypatch.setattr(ingest, "extract_workbook", explode)
    assert len(ingest.run(landing_dir=landing_dir)) == len(config.SHEETS)
