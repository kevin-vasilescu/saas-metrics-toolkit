"""I/O tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from saas_metrics import DataError, load_spend, load_subscriptions


def test_load_basic(fixtures_dir: Path) -> None:
    df = load_subscriptions(fixtures_dir / "basic_subscriptions.csv")
    assert len(df) == 6
    assert str(df["start_date"].dtype).startswith("datetime64")


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DataError, match="file not found"):
        load_subscriptions(tmp_path / "nope.csv")


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "e.csv"
    path.write_text("")
    with pytest.raises(DataError, match="is empty"):
        load_subscriptions(path)


def test_invalid_rows_raise_with_row_numbers(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("customer_id,plan,monthly_price,start_date,end_date\na,p,-1,2024-01-01,\n")
    with pytest.raises(DataError, match="row 2: monthly_price is negative"):
        load_subscriptions(path)


def test_duplicate_warning_emitted(tmp_path: Path) -> None:
    path = tmp_path / "dup.csv"
    row = "a,p,5,2024-01-01,\n"
    path.write_text("customer_id,plan,monthly_price,start_date,end_date\n" + row + row)
    with pytest.warns(UserWarning, match="duplicate row dropped"):
        assert len(load_subscriptions(path)) == 1


def test_load_spend(fixtures_dir: Path) -> None:
    assert load_spend(fixtures_dir / "basic_spend.csv")["marketing_spend"].tolist() == [0, 90, 100]


def test_bad_spend(tmp_path: Path) -> None:
    path = tmp_path / "s.csv"
    path.write_text("month,marketing_spend\n2024-99,5\n")
    with pytest.raises(DataError, match="row 2"):
        load_spend(path)


def test_directory_is_unreadable(tmp_path: Path) -> None:
    with pytest.raises(DataError):
        load_subscriptions(tmp_path)
