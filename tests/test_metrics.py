"""Metrics tests against hand-calculated values.

Fixture basic_subscriptions.csv. A row is active at month end M if start <= M and
end is empty or > M. Month-end MRR:

    Jan: A100 + B50 + D40            = 190  (3 customers)
    Feb: A100 + B50 + C30            = 180  (D ended 02-15)
    Mar: A100 + C80                  = 180  (B ended 03-01, C upgraded 30 -> 80)
    Apr: A100 + C80 + D40            = 220  (D reactivated 04-02)
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from conftest import make_subs
from saas_metrics import DataError, compute_metrics


@pytest.fixture
def monthly(basic_subs: pd.DataFrame, basic_spend: pd.DataFrame) -> pd.DataFrame:
    return compute_metrics(basic_subs, basic_spend).monthly.set_index("month")


def test_mrr_and_arr(monthly: pd.DataFrame) -> None:
    assert monthly["mrr"].tolist() == [190, 180, 180, 220]
    assert monthly["arr"].tolist() == [2280, 2160, 2160, 2640]


def test_first_month_everything_is_new(monthly: pd.DataFrame) -> None:
    jan = monthly.loc["2024-01"]
    assert jan["new_mrr"] == 190
    assert jan["new_customers"] == 3
    assert jan["churned_mrr"] == 0
    assert pd.isna(jan["nrr"])  # starting MRR is zero


def test_february_churn(monthly: pd.DataFrame) -> None:
    feb = monthly.loc["2024-02"]
    # New: C 30. Churned: D 40. Start MRR 190, start customers 3.
    assert feb["new_mrr"] == 30
    assert feb["churned_mrr"] == 40
    assert feb["churned_customers"] == 1
    assert feb["logo_churn_rate"] == pytest.approx(1 / 3)
    assert feb["gross_revenue_churn_rate"] == pytest.approx(40 / 190)
    assert feb["nrr"] == pytest.approx(150 / 190)  # (190 - 40) / 190
    assert feb["grr"] == pytest.approx(150 / 190)
    assert feb["arpa"] == pytest.approx(60)  # 180 / 3


def test_march_upgrade_and_churn(monthly: pd.DataFrame) -> None:
    mar = monthly.loc["2024-03"]
    # Start 180. B churns (50). C expands 30 -> 80 (+50).
    assert mar["expansion_mrr"] == 50
    assert mar["churned_mrr"] == 50
    assert mar["nrr"] == pytest.approx(1.0)  # (180 + 50 - 50) / 180
    assert mar["grr"] == pytest.approx(130 / 180)  # (180 - 50) / 180
    assert mar["quick_ratio"] == pytest.approx(1.0)  # 50 / 50
    assert mar["ltv"] == pytest.approx(216)  # ARPA 90 * 0.8 / (1/3)


def test_reactivation_counts_as_new(monthly: pd.DataFrame) -> None:
    apr = monthly.loc["2024-04"]
    assert apr["new_mrr"] == 40
    assert apr["new_customers"] == 1


def test_zero_churn_gives_none_ltv_and_quick_ratio(monthly: pd.DataFrame) -> None:
    apr = monthly.loc["2024-04"]
    assert apr["logo_churn_rate"] == 0
    assert pd.isna(apr["ltv"])
    assert pd.isna(apr["quick_ratio"])  # denominator is zero


def test_cac_payback_and_ltv_cac(monthly: pd.DataFrame) -> None:
    feb = monthly.loc["2024-02"]
    assert feb["cac"] == pytest.approx(90)  # 90 spend / 1 new customer
    assert feb["cac_payback_months"] == pytest.approx(3.75)  # 90 / (30 * 0.8)
    assert feb["ltv_cac"] == pytest.approx(1.6)  # LTV 60 * 0.8 * 3 = 144; 144 / 90


def test_cac_none_without_new_customers_or_spend(monthly: pd.DataFrame) -> None:
    assert pd.isna(monthly.loc["2024-03", "cac"])  # spend 100, zero new customers
    assert pd.isna(monthly.loc["2024-04", "cac"])  # no spend row


def test_zero_spend_gives_zero_cac_and_no_ratio(monthly: pd.DataFrame) -> None:
    jan = monthly.loc["2024-01"]
    assert jan["cac"] == 0
    assert pd.isna(jan["ltv_cac"])


def test_without_spend_cac_is_none(basic_subs: pd.DataFrame) -> None:
    result = compute_metrics(basic_subs)
    assert result.to_dataframe()["cac"].isna().all()


def test_contraction() -> None:
    # X pays 100 in Jan, drops to 60 in Feb: contraction 40, NRR (100 - 40) / 100.
    subs = make_subs([("X", 100, "2024-01-01", "2024-02-01"), ("X", 60, "2024-02-01", "")])
    feb = compute_metrics(subs).monthly.set_index("month").loc["2024-02"]
    assert feb["contraction_mrr"] == 40
    assert feb["nrr"] == pytest.approx(0.6)
    assert feb["gross_revenue_churn_rate"] == pytest.approx(0.4)


def test_upgrade_and_downgrade_same_month() -> None:
    # U: 50 -> 100 (+50). V: 80 -> 60 (-20). Start MRR 130. NRR (130 + 50 - 20) / 130.
    subs = make_subs(
        [
            ("U", 50, "2024-01-01", "2024-02-01"),
            ("U", 100, "2024-02-01", ""),
            ("V", 80, "2024-01-01", "2024-02-01"),
            ("V", 60, "2024-02-01", ""),
        ]
    )
    feb = compute_metrics(subs).monthly.set_index("month").loc["2024-02"]
    assert feb["expansion_mrr"] == 50
    assert feb["contraction_mrr"] == 20
    assert feb["nrr"] == pytest.approx(160 / 130)
    assert feb["grr"] == pytest.approx(110 / 130)


def test_end_date_on_month_boundary() -> None:
    # Ending on Jan 31 means inactive at Jan 31 month end; ending Feb 1 means active.
    subs = make_subs(
        [("E", 10, "2024-01-01", "2024-01-31"), ("F", 10, "2024-01-01", "2024-02-01"), ("G", 5, "2024-03-01", "")]
    )
    monthly = compute_metrics(subs).monthly.set_index("month")
    assert monthly.loc["2024-01", "mrr"] == 10  # only F
    assert monthly.loc["2024-02", "mrr"] == 0


def test_single_customer_no_crash() -> None:
    subs = make_subs([("S", 25, "2024-05-03", "")])
    result = compute_metrics(subs)
    assert len(result.monthly) == 1
    assert result.monthly["mrr"].iloc[0] == 25


def test_overlapping_rows_sum() -> None:
    subs = make_subs([("O", 10, "2024-01-01", ""), ("O", 5, "2024-01-01", "")])
    assert compute_metrics(subs).monthly["mrr"].iloc[0] == 15


@pytest.mark.parametrize("margin", [0, -0.1, 1.5])
def test_gross_margin_out_of_range(basic_subs: pd.DataFrame, margin: float) -> None:
    with pytest.raises(DataError):
        compute_metrics(basic_subs, gross_margin=margin)


def test_empty_data_rejected() -> None:
    with pytest.raises(DataError):
        compute_metrics(make_subs([]))


def test_gross_margin_one_is_allowed(basic_subs: pd.DataFrame) -> None:
    mar = compute_metrics(basic_subs, gross_margin=1.0).monthly.set_index("month").loc["2024-03"]
    assert mar["ltv"] == pytest.approx(270)  # 90 * 1.0 / (1/3)


def test_no_nan_or_inf_in_json(basic_subs: pd.DataFrame) -> None:
    text = compute_metrics(basic_subs).to_json()
    assert "NaN" not in text
    assert "Infinity" not in text
    assert json.loads(text)["monthly"][0]["nrr"] is None


def test_between_filters_months(basic_subs: pd.DataFrame) -> None:
    result = compute_metrics(basic_subs).between("2024-02", "2024-03")
    assert result.monthly["month"].tolist() == ["2024-02", "2024-03"]
