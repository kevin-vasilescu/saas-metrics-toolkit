"""Self-contained HTML report."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape
from markupsafe import Markup

from saas_metrics.report.charts import line_chart
from saas_metrics.report.markdown import KINDS, LABELS, fmt, fmt_change, missing

if TYPE_CHECKING:
    from saas_metrics.models import MetricsResult

CARD_KEYS = ["mrr", "arr", "active_customers", "nrr", "grr", "logo_churn_rate", "ltv_cac", "quick_ratio"]
TABLE_KEYS = [k for k in LABELS if k not in {"arr"}]


def heat_color(value: float) -> str:
    """Map a retention percentage to a background colour."""
    alpha = max(0.0, min(value, 100.0)) / 100
    return f"rgba(79,70,229,{0.08 + 0.82 * alpha:.2f})"


def render_html(result: MetricsResult) -> str:
    """Render the report as a single self-contained HTML document.

    Args:
        result: Computed metrics.

    Returns:
        HTML text with inline CSS and an inline SVG chart; no external requests.
    """
    env = Environment(
        loader=PackageLoader("saas_metrics.report", "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    monthly = result.to_dataframe()
    latest = monthly.iloc[-1]
    prev = monthly.iloc[-2] if len(monthly) > 1 else pd.Series(dtype=object)
    cards = [
        {
            "label": LABELS[k],
            "value": fmt(latest[k], KINDS[k]),
            "change": fmt_change(latest[k], prev.get(k), KINDS[k]),
        }
        for k in CARD_KEYS
    ]
    rows = [[fmt(r[k], KINDS[k]) if k in KINDS else r[k] for k in ["month", *TABLE_KEYS]] for _, r in monthly.iterrows()]
    cohort_rows = []
    for cohort, row in result.cohorts.iterrows():
        cells = [
            {"text": "", "style": ""}
            if missing(v) or pd.isna(v)
            else {"text": f"{v:.0f}%", "style": f"background:{heat_color(float(v))};color:{'#fff' if v >= 55 else '#111827'}"}
            for v in row.iloc[1:]
        ]
        cohort_rows.append({"cohort": str(cohort), "size": int(row["customers"]), "cells": cells})
    chart = line_chart(list(monthly["month"]), [float(v) for v in monthly["mrr"]])
    return env.get_template("report.html.j2").render(
        title="SaaS Metrics Report",
        first=monthly["month"].iloc[0],
        last=monthly["month"].iloc[-1],
        months=len(monthly),
        margin=f"{result.gross_margin:.0%}",
        cards=cards,
        headers=["Month", *[LABELS[k] for k in TABLE_KEYS]],
        rows=rows,
        cohort_headers=[c.upper() for c in result.cohorts.columns[1:]],
        cohort_rows=cohort_rows,
        chart=Markup(chart),
    )
