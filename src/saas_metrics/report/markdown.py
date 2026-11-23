"""Markdown report."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from saas_metrics.models import MetricsResult

KINDS = {
    "mrr": "money",
    "arr": "money",
    "new_mrr": "money",
    "churned_mrr": "money",
    "expansion_mrr": "money",
    "contraction_mrr": "money",
    "active_customers": "int",
    "new_customers": "int",
    "churned_customers": "int",
    "logo_churn_rate": "rate",
    "gross_revenue_churn_rate": "rate",
    "nrr": "rate",
    "grr": "rate",
    "arpa": "money",
    "ltv": "money",
    "cac": "money",
    "cac_payback_months": "months",
    "ltv_cac": "ratio",
    "quick_ratio": "ratio",
}

LABELS = {
    "mrr": "MRR",
    "arr": "ARR",
    "new_mrr": "New MRR",
    "churned_mrr": "Churned MRR",
    "expansion_mrr": "Expansion MRR",
    "contraction_mrr": "Contraction MRR",
    "active_customers": "Active customers",
    "new_customers": "New customers",
    "churned_customers": "Churned customers",
    "logo_churn_rate": "Logo churn",
    "gross_revenue_churn_rate": "Gross revenue churn",
    "nrr": "NRR",
    "grr": "GRR",
    "arpa": "ARPA",
    "ltv": "LTV",
    "cac": "CAC",
    "cac_payback_months": "CAC payback (months)",
    "ltv_cac": "LTV:CAC",
    "quick_ratio": "Quick ratio",
}

KPI_KEYS = [
    "mrr", "arr", "active_customers", "new_mrr", "churned_mrr", "expansion_mrr",
    "contraction_mrr", "nrr", "grr", "logo_churn_rate", "arpa", "ltv", "cac",
    "cac_payback_months", "ltv_cac", "quick_ratio",
]  # fmt: skip


def missing(value: object) -> bool:
    """Return True for None and NaN."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def fmt(value: object, kind: str) -> str:
    """Format a metric value for display; missing values become ``n/a``."""
    if missing(value):
        return "n/a"
    x = float(value)  # type: ignore[arg-type]
    if kind == "money":
        return f"{x:,.2f}"
    if kind == "int":
        return f"{x:,.0f}"
    if kind == "rate":
        return f"{x * 100:.1f}%"
    if kind == "ratio":
        return f"{x:.2f}x"
    return f"{x:.1f}"


def fmt_change(latest: object, previous: object, kind: str) -> str:
    """Format the change between two values (percentage points for rates)."""
    if missing(latest) or missing(previous):
        return "n/a"
    diff = float(latest) - float(previous)  # type: ignore[arg-type]
    if kind == "rate":
        return f"{diff * 100:+.1f} pp"
    if kind == "ratio":
        return f"{diff:+.2f}x"
    if kind == "int":
        return f"{diff:+,.0f}"
    if kind == "months":
        return f"{diff:+.1f}"
    return f"{diff:+,.2f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-flavoured Markdown table."""
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join("---:" if i else "---" for i in range(len(headers))) + "|"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def kpi_rows(result: MetricsResult) -> list[list[str]]:
    """Rows of (label, latest, previous, change) for the KPI table."""
    monthly = result.to_dataframe()
    latest = monthly.iloc[-1]
    prev = monthly.iloc[-2] if len(monthly) > 1 else pd.Series(dtype=object)
    rows = []
    for key in KPI_KEYS:
        kind = KINDS[key]
        before = prev.get(key)
        rows.append(
            [LABELS[key], fmt(latest[key], kind), fmt(before, kind), fmt_change(latest[key], before, kind)]
        )
    return rows


def cohort_cells(result: MetricsResult) -> tuple[list[str], list[list[str]]]:
    """Headers and string rows of the cohort matrix."""
    cohorts = result.cohorts
    headers = ["Cohort", "Customers", *[c.upper() for c in cohorts.columns[1:]]]
    rows = []
    for cohort, row in cohorts.iterrows():
        cells = ["" if pd.isna(v) else f"{v:.0f}%" for v in row.iloc[1:]]
        rows.append([str(cohort), str(int(row["customers"])), *cells])
    return headers, rows


def render_markdown(result: MetricsResult) -> str:
    """Render the full Markdown report.

    Args:
        result: Computed metrics.

    Returns:
        Markdown text ending in a newline.
    """
    monthly = result.to_dataframe()
    first, last = monthly["month"].iloc[0], monthly["month"].iloc[-1]
    parts = [
        "# SaaS Metrics Report",
        f"Period: {first} to {last} ({len(monthly)} months). Gross margin: {result.gross_margin:.0%}.",
        f"## Key metrics: {last} vs previous month",
        table(["Metric", last, "Previous", "Change"], kpi_rows(result)),
        "## Monthly metrics",
        table(
            ["Month", "MRR", "New", "Expansion", "Contraction", "Churned", "Customers", "Logo churn", "NRR", "GRR"],
            [
                [
                    r["month"],
                    fmt(r["mrr"], "money"),
                    fmt(r["new_mrr"], "money"),
                    fmt(r["expansion_mrr"], "money"),
                    fmt(r["contraction_mrr"], "money"),
                    fmt(r["churned_mrr"], "money"),
                    fmt(r["active_customers"], "int"),
                    fmt(r["logo_churn_rate"], "rate"),
                    fmt(r["nrr"], "rate"),
                    fmt(r["grr"], "rate"),
                ]
                for _, r in monthly.iterrows()
            ],
        ),
        "## Unit economics",
        table(
            ["Month", "ARPA", "LTV", "CAC", "Payback (months)", "LTV:CAC", "Quick ratio"],
            [
                [
                    r["month"],
                    fmt(r["arpa"], "money"),
                    fmt(r["ltv"], "money"),
                    fmt(r["cac"], "money"),
                    fmt(r["cac_payback_months"], "months"),
                    fmt(r["ltv_cac"], "ratio"),
                    fmt(r["quick_ratio"], "ratio"),
                ]
                for _, r in monthly.iterrows()
            ],
        ),
        "## Cohort retention",
        "Share of each cohort still active N months after its first month.",
        table(*cohort_cells(result)),
    ]
    return "\n\n".join(parts) + "\n"
