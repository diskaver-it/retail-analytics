import pytest

from retail_analytics import warehouse


def test_load_raw_picks_up_every_parquet_in_landing(landing_dir, tmp_path):
    rows = warehouse.load_raw(landing_dir=landing_dir, warehouse=tmp_path / "test.duckdb")
    assert rows == 5


def test_load_raw_records_which_sheet_a_row_came_from(landing_dir, tmp_path):
    db = tmp_path / "test.duckdb"
    warehouse.load_raw(landing_dir=landing_dir, warehouse=db)

    with warehouse.connect(db, read_only=True) as con:
        counts = dict(con.execute(
            f"SELECT source_sheet, count(*) FROM {warehouse.RAW_TABLE} GROUP BY 1"
        ).fetchall())

    assert counts == {"year_2009_2010": 3, "year_2010_2011": 2}


def test_load_raw_complains_about_an_empty_landing(tmp_path):
    empty = tmp_path / "landing"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        warehouse.load_raw(landing_dir=empty, warehouse=tmp_path / "test.duckdb")


def test_load_raw_is_idempotent(landing_dir, tmp_path):
    db = tmp_path / "test.duckdb"
    first = warehouse.load_raw(landing_dir=landing_dir, warehouse=db)
    second = warehouse.load_raw(landing_dir=landing_dir, warehouse=db)
    assert first == second == 5


def test_profile_counts_the_awkward_rows(landing_dir, tmp_path):
    db = tmp_path / "test.duckdb"
    warehouse.load_raw(landing_dir=landing_dir, warehouse=db)
    stats = warehouse.profile(warehouse=db)

    assert stats["rows"] == 5
    assert stats["invoices"] == 4            # two lines share invoice 536365
    assert stats["customers"] == 2           # the null does not count as a third
    assert stats["rows_without_customer"] == 1
    assert stats["cancellation_rows"] == 1
    assert stats["negative_quantity_rows"] == 1
    assert str(stats["first_day"]) == "2009-12-01"
    assert str(stats["last_day"]) == "2010-01-05"
