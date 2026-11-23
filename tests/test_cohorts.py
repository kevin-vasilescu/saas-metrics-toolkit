"""Cohort tests.

Jan cohort = A, B, D (3 customers); Feb cohort = C (1 customer).
Active at month end: Jan {A,B,D}, Feb {A,B,C}, Mar {A,C}, Apr {A,C,D}.
"""

from __future__ import annotations

import pandas as pd
import pytest

from conftest import make_subs
from saas_metrics import cohort_retention


def test_jan_cohort(basic_subs: pd.DataFrame) -> None:
    jan = cohort_retention(basic_subs).loc["2024-01"]
    assert jan["customers"] == 3
    assert jan["m0"] == pytest.approx(100)  # 3 / 3
    assert jan["m1"] == pytest.approx(200 / 3)  # A, B of 3
    assert jan["m2"] == pytest.approx(100 / 3)  # A of 3
    assert jan["m3"] == pytest.approx(200 / 3)  # A and reactivated D


def test_feb_cohort_has_no_future_months(basic_subs: pd.DataFrame) -> None:
    feb = cohort_retention(basic_subs).loc["2024-02"]
    assert feb["customers"] == 1
    assert [feb["m0"], feb["m1"], feb["m2"]] == [100, 100, 100]
    assert pd.isna(feb["m3"])


def test_empty_input() -> None:
    assert cohort_retention(make_subs([])).empty
