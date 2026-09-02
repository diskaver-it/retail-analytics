"""The fixture is only useful if it still contains the cases the models handle.

Every assertion here corresponds to a branch in the dbt models. If the generator
drifts and stops producing guests, or returns, or postage lines, the dbt tests in
CI would go green while testing nothing - these tests are what stops that.
"""
import pandas as pd

from retail_analytics import config, synthetic, warehouse


def test_columns_match_the_raw_contract():
    df = synthetic.transactions(n_customers=40, months=12)
    assert list(df.columns) == list(config.COLUMNS)


def test_generator_is_deterministic():
    left = synthetic.transactions(n_customers=40, months=12, seed=3)
    right = synthetic.transactions(n_customers=40, months=12, seed=3)
    pd.testing.assert_frame_equal(left, right)


def test_fixture_contains_every_awkward_case():
    df = synthetic.transactions(n_customers=200, months=18)

    assert df["customer_id"].isna().any(), "no guest lines"
    assert df["invoice_no"].str.startswith("C").any(), "no cancellations"
    assert (df["quantity"] < 0).any(), "no negative quantities"
    assert (df["unit_price"] == 0).any(), "no zero-priced lines"
    assert df["stock_code"].isin(synthetic.ADMIN_CODES).any(), "no admin lines"
    assert df.duplicated().any(), "no exact duplicate rows"


def test_customers_span_several_cohorts_and_some_come_back():
    df = synthetic.transactions(n_customers=200, months=18)
    identified = df[df["customer_id"].notna() & ~df["invoice_no"].str.startswith("C")]

    first_month = identified.groupby("customer_id")["invoice_ts"].min().dt.to_period("M")
    orders = identified.groupby("customer_id")["invoice_no"].nunique()

    assert first_month.nunique() > 6, "cohorts all land in the same month"
    assert (orders > 1).sum() > 10, "nobody ever comes back, so retention is untestable"


def test_build_warehouse_creates_a_loadable_raw_table(tmp_path):
    db = tmp_path / "synthetic.duckdb"
    rows = synthetic.build_warehouse(db)

    stats = warehouse.profile(warehouse=db)
    assert stats["rows"] == rows
    assert stats["cancellation_rows"] > 0
    assert stats["rows_without_customer"] > 0
