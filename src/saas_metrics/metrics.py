"""Monthly SaaS metric computation."""

from __future__ import annotations

import pandas as pd

from saas_metrics.cohorts import cohort_retention, customer_mrr, month_range
from saas_metrics.models import MONTHLY_COLUMNS, DataError, MetricsResult


def _div(num: pd.Series, den: pd.Series) -> pd.Series:
    """Divide, returning NaN where the denominator is zero."""
    return num / den.where(den != 0)


def compute_metrics(
    subs: pd.DataFrame,
    spend: pd.DataFrame | None = None,
    gross_margin: float = 0.8,
) -> MetricsResult:
    """Compute monthly MRR movements, churn, retention and unit economics.

    Args:
        subs: Cleaned subscriptions from ``load_subscriptions``.
        spend: Optional spend table from ``load_spend``, used for CAC.
        gross_margin: Gross margin in the interval (0, 1].

    Returns:
        A ``MetricsResult`` with the monthly table and cohort matrix.

    Raises:
        DataError: If ``gross_margin`` is out of range or ``subs`` is empty.
    """
    if not 0 < gross_margin <= 1:
        raise DataError("gross_margin must be greater than 0 and at most 1")
    if subs.empty:
        raise DataError("no subscription rows to analyse")

    months = month_range(subs)
    cur = customer_mrr(subs, months)
    prev = cur.shift(1, axis=1, fill_value=0.0)
    delta = cur - prev
    was, now = prev > 0, cur > 0
    both = was & now

    m = pd.DataFrame(index=months)
    m["mrr"] = cur.sum()
    m["new_mrr"] = cur.where(~was & now, 0.0).sum()
    m["churned_mrr"] = prev.where(was & ~now, 0.0).sum()
    m["expansion_mrr"] = delta.where(both & (delta > 0), 0.0).sum()
    m["contraction_mrr"] = (-delta).where(both & (delta < 0), 0.0).sum()
    m["active_customers"] = now.sum()
    m["new_customers"] = (~was & now).sum()
    m["churned_customers"] = (was & ~now).sum()
    start_mrr = prev.sum()
    start_customers = was.sum()

    m["arr"] = m["mrr"] * 12
    m["logo_churn_rate"] = _div(m["churned_customers"], start_customers)
    m["gross_revenue_churn_rate"] = _div(m["churned_mrr"] + m["contraction_mrr"], start_mrr)
    m["nrr"] = _div(start_mrr + m["expansion_mrr"] - m["contraction_mrr"] - m["churned_mrr"], start_mrr)
    m["grr"] = _div(start_mrr - m["contraction_mrr"] - m["churned_mrr"], start_mrr)
    m["arpa"] = _div(m["mrr"], m["active_customers"])
    m["ltv"] = _div(m["arpa"] * gross_margin, m["logo_churn_rate"])
    if spend is not None:
        spent = spend.set_index("month")["marketing_spend"].reindex(months.strftime("%Y-%m"))
        m["cac"] = _div(pd.Series(spent.to_numpy(), index=months), m["new_customers"])
    else:
        m["cac"] = float("nan")
    new_arpa = _div(m["new_mrr"], m["new_customers"])
    m["cac_payback_months"] = _div(m["cac"], new_arpa * gross_margin)
    m["ltv_cac"] = _div(m["ltv"], m["cac"])
    m["quick_ratio"] = _div(m["new_mrr"] + m["expansion_mrr"], m["churned_mrr"] + m["contraction_mrr"])

    m.insert(0, "month", months.strftime("%Y-%m"))
    monthly = m.reset_index(drop=True)[MONTHLY_COLUMNS]
    return MetricsResult(monthly, cohort_retention(subs), gross_margin)
