"""Validation tests."""

from __future__ import annotations

import pandas as pd

from saas_metrics.validation import validate_spend, validate_subscriptions

COLS = ["customer_id", "plan", "monthly_price", "start_date", "end_date"]


def raw(*rows: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=COLS)


def messages(report_items: list) -> list[str]:  # type: ignore[type-arg]
    return [str(i) for i in report_items]


def test_valid_rows() -> None:
    df, rep = validate_subscriptions(raw(("a", "p", "10", "2024-01-01", "")))
    assert rep.ok
    assert df["monthly_price"].iloc[0] == 10.0


def test_missing_column() -> None:
    _, rep = validate_subscriptions(pd.DataFrame({"customer_id": ["a"]}))
    assert "missing required column(s): plan" in messages(rep.errors)[0]


def test_empty_frame() -> None:
    _, rep = validate_subscriptions(raw())
    assert "no data rows" in messages(rep.errors)[0]


def test_row_numbers_and_each_error() -> None:
    _, rep = validate_subscriptions(
        raw(
            ("", "p", "10", "2024-01-01", ""),
            ("b", "p", "abc", "2024-01-01", ""),
            ("c", "p", "-5", "2024-01-01", ""),
            ("d", "p", "5", "not-a-date", ""),
            ("e", "p", "5", "2024-02-01", "2024-01-01"),
            ("f", "p", "5", "2024-02-01", "garbage"),
        )
    )
    text = messages(rep.errors)
    assert text[0] == "row 2: customer_id is empty"
    assert any(t.startswith("row 3:") and "not a number" in t for t in text)
    assert any(t.startswith("row 4:") and "negative" in t for t in text)
    assert any(t.startswith("row 5:") and "start_date" in t for t in text)
    assert any(t.startswith("row 6:") and "before start_date" in t for t in text)
    assert any(t.startswith("row 7:") and "end_date is not a valid" in t for t in text)


def test_duplicates_dropped_with_warning() -> None:
    df, rep = validate_subscriptions(raw(("a", "p", "10", "2024-01-01", ""), ("a", "p", "10", "2024-01-01", "")))
    assert len(df) == 1
    assert messages(rep.warnings) == ["row 3: duplicate row dropped"]


def test_overlap_warns_but_passes() -> None:
    df, rep = validate_subscriptions(
        raw(("a", "p", "10", "2024-01-01", "2024-03-01"), ("a", "p", "10", "2024-02-01", ""))
    )
    assert rep.ok
    assert len(df) == 2
    assert "overlaps row 2" in messages(rep.warnings)[0]


def test_adjacent_rows_do_not_overlap() -> None:
    _, rep = validate_subscriptions(
        raw(("a", "p", "10", "2024-01-01", "2024-02-01"), ("a", "p", "10", "2024-02-01", ""))
    )
    assert not rep.warnings


def test_spend_validation() -> None:
    df, rep = validate_spend(pd.DataFrame({"month": ["2024-01", "2024-01"], "marketing_spend": ["5", "7"]}))
    assert df["marketing_spend"].tolist() == [7.0]
    assert len(rep.warnings) == 1
    _, bad = validate_spend(pd.DataFrame({"month": ["2024-13", "2024-02"], "marketing_spend": ["5", "-1"]}))
    assert len(bad.errors) == 2
    _, missing = validate_spend(pd.DataFrame({"month": ["2024-01"]}))
    assert not missing.ok
