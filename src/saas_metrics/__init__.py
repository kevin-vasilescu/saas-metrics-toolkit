"""Turn raw subscription data into SaaS metrics and cohort retention reports."""

from saas_metrics.cohorts import cohort_retention
from saas_metrics.io import load_spend, load_subscriptions
from saas_metrics.metrics import compute_metrics
from saas_metrics.models import DataError, MetricsResult

__version__ = "0.1.0"

__all__ = [
    "DataError",
    "MetricsResult",
    "__version__",
    "cohort_retention",
    "compute_metrics",
    "load_spend",
    "load_subscriptions",
]
