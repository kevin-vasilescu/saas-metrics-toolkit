"""Validation of raw subscription and spend data."""

from __future__ import annotations

import pandas as pd

from saas_metrics.models import Issue, ValidationReport

SUBSCRIPTION_COLUMNS = ["customer_id", "plan", "monthly_price", "start_date", "end_date"]
SPEND_COLUMNS = ["month", "marketing_spend"]


def _missing_columns(raw: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in raw.columns]


def validate_subscriptions(raw: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """Validate and clean a raw (all-string) subscriptions table.

    Args:
        raw: Frame read with every column as string. The index must be the
            zero-based data row position.

    Returns:
        The cleaned frame (typed, duplicates dropped) and the report. The frame
        is empty when the report contains errors.
    """
    report = ValidationReport()
    missing = _missing_columns(raw, SUBSCRIPTION_COLUMNS)
    if missing:
        report.errors.append(Issue(None, f"missing required column(s): {', '.join(missing)}"))
        return raw.iloc[0:0], report
    if raw.empty:
        report.errors.append(Issue(None, "file contains no data rows"))
        return raw, report

    df = raw[SUBSCRIPTION_COLUMNS].apply(lambda s: s.str.strip())
    line = pd.Series(df.index + 2, index=df.index)

    def flag(mask: pd.Series, message: str) -> None:
        for row in line[mask]:
            report.errors.append(Issue(int(row), message))

    flag(df["customer_id"] == "", "customer_id is empty")
    price = pd.to_numeric(df["monthly_price"], errors="coerce")
    flag(price.isna() | ~price.abs().lt(float("inf")), "monthly_price is not a number")
    flag(price < 0, "monthly_price is negative")
    start = pd.to_datetime(df["start_date"], format="%Y-%m-%d", errors="coerce")
    flag(start.isna(), "start_date is missing or not a valid YYYY-MM-DD date")
    has_end = df["end_date"] != ""
    end = pd.to_datetime(df["end_date"].where(has_end), format="%Y-%m-%d", errors="coerce")
    flag(has_end & end.isna(), "end_date is not a valid YYYY-MM-DD date")
    flag(end < start, "end_date is before start_date")
    if report.errors:
        report.errors.sort(key=lambda i: i.row or 0)
        return raw.iloc[0:0], report

    clean = pd.DataFrame(
        {
            "customer_id": df["customer_id"],
            "plan": df["plan"],
            "monthly_price": price.astype(float),
            "start_date": start,
            "end_date": end,
        }
    )
    dup = clean.duplicated(keep="first")
    for row in line[dup]:
        report.warnings.append(Issue(int(row), "duplicate row dropped"))
    clean, line = clean[~dup], line[~dup]
    report.warnings.extend(_overlap_warnings(clean, line))
    return clean.reset_index(drop=True), report


def _overlap_warnings(clean: pd.DataFrame, line: pd.Series) -> list[Issue]:
    far = pd.Timestamp("2200-01-01")
    frame = clean.assign(_end=clean["end_date"].fillna(far), _line=line).sort_values(
        ["customer_id", "plan", "start_date"]
    )
    group = frame.groupby(["customer_id", "plan"], sort=False)
    prev_end = group["_end"].shift(1)
    prev_line = group["_line"].shift(1)
    hit = prev_end > frame["start_date"]
    return [
        Issue(int(r), f"overlaps row {int(p)} for the same customer and plan")
        for r, p in zip(frame.loc[hit, "_line"], prev_line[hit], strict=True)
    ]


def validate_spend(raw: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """Validate and clean a raw (all-string) spend table.

    Args:
        raw: Frame read with every column as string.

    Returns:
        A frame with ``month`` (YYYY-MM string) and ``marketing_spend`` columns,
        and the report. The frame is empty when there are errors.
    """
    report = ValidationReport()
    missing = _missing_columns(raw, SPEND_COLUMNS)
    if missing:
        report.errors.append(Issue(None, f"missing required column(s): {', '.join(missing)}"))
        return raw.iloc[0:0], report
    df = raw[SPEND_COLUMNS].apply(lambda s: s.str.strip())
    line = pd.Series(df.index + 2, index=df.index)
    month = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    spend = pd.to_numeric(df["marketing_spend"], errors="coerce")
    for row in line[month.isna()]:
        report.errors.append(Issue(int(row), "month is not a valid YYYY-MM value"))
    for row in line[spend.isna() | (spend < 0)]:
        report.errors.append(Issue(int(row), "marketing_spend must be a non-negative number"))
    if report.errors:
        report.errors.sort(key=lambda i: i.row or 0)
        return raw.iloc[0:0], report
    out = pd.DataFrame({"month": month.dt.strftime("%Y-%m"), "marketing_spend": spend.astype(float)})
    dup = out["month"].duplicated(keep="last")
    for row in line[dup]:
        report.warnings.append(Issue(int(row), "duplicate month ignored; the last value is used"))
    return out[~dup].reset_index(drop=True), report
