"""Sample data tests."""

from __future__ import annotations

import pandas as pd
import pytest

from saas_metrics.sample_data import generate_sample
from saas_metrics.validation import validate_subscriptions


def test_deterministic() -> None:
    a, sa = generate_sample(50, 12, seed=1)
    b, sb = generate_sample(50, 12, seed=1)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(sa, sb)


def test_seed_changes_output() -> None:
    a, _ = generate_sample(50, 12, seed=1)
    b, _ = generate_sample(50, 12, seed=2)
    assert not a.equals(b)


def test_output_is_valid_and_realistic() -> None:
    subs, spend = generate_sample(300, 24, seed=7)
    _, report = validate_subscriptions(subs.astype(str).replace("nan", ""))
    assert report.ok
    assert not report.warnings
    assert len(spend) == 24
    assert subs["plan"].nunique() == 3
    assert subs["customer_id"].nunique() == 300
    assert (subs["end_date"] != "").any()
    assert subs.groupby("customer_id").size().max() > 1


def test_invalid_arguments() -> None:
    with pytest.raises(ValueError):
        generate_sample(0, 12)
