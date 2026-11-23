"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from saas_metrics import load_spend, load_subscriptions

FIXTURES = Path(__file__).parent / "fixtures"


def make_subs(rows: list[tuple[str, float, str, str]]) -> pd.DataFrame:
    """Build a cleaned subscriptions frame from (customer, price, start, end) tuples."""
    df = pd.DataFrame(rows, columns=["customer_id", "monthly_price", "start_date", "end_date"])
    df["plan"] = "p"
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"].replace("", None))
    return df


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def basic_subs() -> pd.DataFrame:
    return load_subscriptions(FIXTURES / "basic_subscriptions.csv")


@pytest.fixture
def basic_spend() -> pd.DataFrame:
    return load_spend(FIXTURES / "basic_spend.csv")
