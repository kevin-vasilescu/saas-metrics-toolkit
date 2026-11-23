"""Reading CSV files."""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from saas_metrics.models import DataError, ValidationReport
from saas_metrics.validation import validate_spend, validate_subscriptions


def _read_raw(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    try:
        return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except FileNotFoundError:
        raise DataError(f"file not found: {p}") from None
    except pd.errors.EmptyDataError:
        raise DataError(f"{p} is empty") from None
    except (pd.errors.ParserError, UnicodeDecodeError, IsADirectoryError, PermissionError) as exc:
        raise DataError(f"cannot read {p}: {exc}") from None


def read_subscriptions(path: str | Path) -> tuple[pd.DataFrame, ValidationReport]:
    """Read and validate a subscriptions CSV without raising on bad content.

    Args:
        path: Path to the CSV file.

    Returns:
        Cleaned data and the validation report.

    Raises:
        DataError: If the file is missing, empty or unreadable.
    """
    return validate_subscriptions(_read_raw(path))


def _raise_or_warn(report: ValidationReport, name: str) -> None:
    if report.errors:
        details = "\n".join(f"  - {i}" for i in report.errors)
        raise DataError(f"{name} has {len(report.errors)} problem(s):\n{details}")
    for issue in report.warnings:
        warnings.warn(f"{name}: {issue}", stacklevel=3)


def load_subscriptions(path: str | Path) -> pd.DataFrame:
    """Load a subscriptions CSV.

    Args:
        path: Path to a CSV with customer_id, plan, monthly_price, start_date, end_date.

    Returns:
        A typed DataFrame with duplicate rows removed. Warnings are emitted through
        the ``warnings`` module.

    Raises:
        DataError: If the file is unreadable or contains invalid rows.
    """
    df, report = read_subscriptions(path)
    _raise_or_warn(report, Path(path).name)
    return df


def load_spend(path: str | Path) -> pd.DataFrame:
    """Load a marketing spend CSV.

    Args:
        path: Path to a CSV with month (YYYY-MM) and marketing_spend columns.

    Returns:
        A DataFrame with ``month`` strings and float ``marketing_spend``.

    Raises:
        DataError: If the file is unreadable or contains invalid rows.
    """
    df, report = validate_spend(_read_raw(path))
    _raise_or_warn(report, Path(path).name)
    return df
