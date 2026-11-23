"""Cohort retention."""

from __future__ import annotations

import numpy as np
import pandas as pd

FAR_FUTURE = np.datetime64("2200-01-01")


def month_range(subs: pd.DataFrame) -> pd.PeriodIndex:
    """Return every calendar month spanned by the subscription data."""
    first = subs["start_date"].min()
    last = max(subs["start_date"].max(), subs["end_date"].max())
    return pd.period_range(first.to_period("M"), last.to_period("M"), freq="M")


def customer_mrr(subs: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    """Compute each customer's MRR at the end of each month.

    A row is active in a month if ``start_date <= month_end`` and the end date is
    empty or later than ``month_end``.

    Args:
        subs: Cleaned subscriptions.
        months: Months to evaluate.

    Returns:
        Frame indexed by customer_id with one column per month.
    """
    month_end = months.to_timestamp(how="end").normalize().to_numpy().astype("datetime64[D]")
    start = subs["start_date"].to_numpy().astype("datetime64[D]")
    end = subs["end_date"].to_numpy().astype("datetime64[D]")
    end = np.where(np.isnat(end), FAR_FUTURE, end)
    active = (start[:, None] <= month_end[None, :]) & (end[:, None] > month_end[None, :])
    values = subs["monthly_price"].to_numpy()[:, None] * active
    frame = pd.DataFrame(values, columns=months)
    return frame.groupby(subs["customer_id"].to_numpy()).sum().round(6)


def cohort_retention(subs: pd.DataFrame) -> pd.DataFrame:
    """Build the cohort retention matrix.

    The cohort is the month of a customer's first-ever start_date. Each value is
    the percentage of that cohort with MRR above zero N months later.

    Args:
        subs: Cleaned subscriptions from ``load_subscriptions``.

    Returns:
        Frame indexed by cohort month (YYYY-MM) with a ``customers`` column and
        ``m0``, ``m1``, ... columns. Months that have not happened yet are NaN.
    """
    if subs.empty:
        return pd.DataFrame(columns=["customers"]).rename_axis("cohort")
    months = month_range(subs)
    mrr = customer_mrr(subs, months)
    first = subs.groupby("customer_id")["start_date"].min().dt.to_period("M")
    cohort_pos = pd.Series(months.get_indexer(first.reindex(mrr.index)), index=mrr.index)
    active = (mrr.to_numpy() > 0).astype(float)
    n = len(months)
    rows = {}
    for pos, idx in cohort_pos.groupby(cohort_pos).groups.items():
        members = mrr.index.get_indexer(idx)
        share = active[members].mean(axis=0) * 100
        row = np.full(n, np.nan)
        row[: n - pos] = share[pos:]
        rows[str(months[pos])] = [len(members), *row]
    columns = ["customers", *[f"m{i}" for i in range(n)]]
    out = pd.DataFrame.from_dict(rows, orient="index", columns=columns).rename_axis("cohort")
    out["customers"] = out["customers"].astype(int)
    return out.sort_index().dropna(axis=1, how="all")
