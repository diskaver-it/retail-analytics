import pandas as pd
import pytest

from retail_analytics import config


def sample_frame() -> pd.DataFrame:
    """Five rows carrying the quirks the real file has.

    In order: an ordinary sale, a second line on the same invoice, a cancellation
    (C prefix, negative quantity), a sale with no customer id, and a zero-priced
    row. The source is full of the last three and every one of them will quietly
    corrupt a metric that ignores it.
    """
    rows = [
        ("536365", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 6, "2009-12-01 08:26", 2.55, 17850.0, "United Kingdom"),
        ("536365", "71053", "WHITE METAL LANTERN", 6, "2009-12-01 08:26", 3.39, 17850.0, "United Kingdom"),
        ("C536379", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", -6, "2009-12-02 09:41", 2.55, 17850.0, "United Kingdom"),
        ("536380", "22633", "HAND WARMER UNION JACK", 2, "2010-01-05 11:02", 1.85, None, "France"),
        ("536381", "22633", "HAND WARMER UNION JACK", 1, "2010-01-05 11:30", 0.00, 12583.0, "France"),
    ]
    df = pd.DataFrame(rows, columns=list(config.COLUMNS))
    df["invoice_ts"] = pd.to_datetime(df["invoice_ts"])
    return df


@pytest.fixture
def landing_dir(tmp_path):
    """A landing folder holding the sample split across two sheet files."""
    directory = tmp_path / "landing"
    directory.mkdir()
    df = sample_frame()
    df.iloc[:3].to_parquet(directory / "year_2009_2010.parquet", index=False)
    df.iloc[3:].to_parquet(directory / "year_2010_2011.parquet", index=False)
    return directory
