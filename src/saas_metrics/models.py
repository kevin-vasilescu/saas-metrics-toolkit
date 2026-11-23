"""Shared data models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

MONTHLY_COLUMNS = [
    "month",
    "mrr",
    "arr",
    "new_mrr",
    "churned_mrr",
    "expansion_mrr",
    "contraction_mrr",
    "active_customers",
    "new_customers",
    "churned_customers",
    "logo_churn_rate",
    "gross_revenue_churn_rate",
    "nrr",
    "grr",
    "arpa",
    "ltv",
    "cac",
    "cac_payback_months",
    "ltv_cac",
    "quick_ratio",
]


class DataError(Exception):
    """Raised when input data is invalid or cannot be read."""


@dataclass(frozen=True)
class Issue:
    """A single validation finding.

    Attributes:
        row: CSV line number (header is line 1), or None for file-level issues.
        message: Human-readable description.
    """

    row: int | None
    message: str

    def __str__(self) -> str:
        return f"row {self.row}: {self.message}" if self.row else self.message


@dataclass
class ValidationReport:
    """Errors and warnings found while validating a file."""

    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether the file has no blocking errors."""
        return not self.errors


def to_none(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with NaN and infinite values replaced by None."""
    out = df.replace([float("inf"), float("-inf")], float("nan")).astype(object)
    return out.where(out.notna(), None)


@dataclass
class MetricsResult:
    """Monthly SaaS metrics and cohort retention.

    Attributes:
        monthly: One row per month with all metric columns.
        cohorts: Cohort retention matrix (percent of cohort still active).
        gross_margin: Gross margin used for LTV and CAC payback.
    """

    monthly: pd.DataFrame
    cohorts: pd.DataFrame
    gross_margin: float

    def to_dataframe(self) -> pd.DataFrame:
        """Return the monthly metrics with missing values as None."""
        return to_none(self.monthly)

    def between(self, start: str | None = None, end: str | None = None) -> MetricsResult:
        """Restrict the monthly table to months in ``[start, end]`` (YYYY-MM)."""
        months = self.monthly["month"]
        mask = pd.Series(True, index=self.monthly.index)
        if start:
            mask &= months >= start
        if end:
            mask &= months <= end
        return MetricsResult(self.monthly[mask].reset_index(drop=True), self.cohorts, self.gross_margin)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary with a stable schema."""
        cohorts = to_none(self.cohorts.reset_index())
        return {
            "gross_margin": self.gross_margin,
            "monthly": self.to_dataframe().to_dict(orient="records"),
            "cohorts": cohorts.to_dict(orient="records"),
        }

    def to_json(self) -> str:
        """Serialise the result as JSON."""
        return json.dumps(self.to_dict(), indent=2, default=float)

    def to_csv(self) -> str:
        """Serialise the monthly table as CSV."""
        return self.monthly.to_csv(index=False, float_format="%.6g", lineterminator="\n")

    def to_markdown(self) -> str:
        """Render the Markdown report."""
        from saas_metrics.report.markdown import render_markdown

        return render_markdown(self)

    def to_html(self) -> str:
        """Render the self-contained HTML report."""
        from saas_metrics.report.html import render_html

        return render_html(self)
