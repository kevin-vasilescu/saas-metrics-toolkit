"""Deterministic synthetic data generation."""

from __future__ import annotations

import numpy as np
import pandas as pd

PLANS = {"starter": 29.0, "pro": 79.0, "business": 199.0}
TIERS = list(PLANS)
CHURN_P, UPGRADE_P, DOWNGRADE_P, REACTIVATE_P = 0.04, 0.04, 0.02, 0.03
INACTIVE = -1


def _next_state(state: int, draw: float) -> int:
    if state == INACTIVE:
        return 0 if draw < REACTIVATE_P else INACTIVE
    if draw < CHURN_P:
        return INACTIVE
    if draw < CHURN_P + UPGRADE_P and state < len(TIERS) - 1:
        return state + 1
    if draw < CHURN_P + UPGRADE_P + DOWNGRADE_P and state > 0:
        return state - 1
    return state


def _runs(states: list[int]) -> list[tuple[int, int, int]]:
    """Collapse per-month states into ``(state, first_index, last_index)`` runs."""
    runs: list[tuple[int, int, int]] = []
    for i, s in enumerate(states):
        if runs and runs[-1][0] == s:
            runs[-1] = (s, runs[-1][1], i)
        else:
            runs.append((s, i, i))
    return runs


def generate_sample(
    customers: int = 500, months: int = 24, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate realistic synthetic subscription and spend data.

    Customers sign up with growing volume, upgrade, downgrade, churn and
    sometimes reactivate. Output is fully determined by the arguments.

    Args:
        customers: Number of customers.
        months: Number of months to simulate, starting 2023-01.
        seed: Random seed.

    Returns:
        ``(subscriptions, spend)`` frames matching the CSV formats.

    Raises:
        ValueError: If ``customers`` or ``months`` is below 1.
    """
    if customers < 1 or months < 1:
        raise ValueError("customers and months must be at least 1")
    rng = np.random.default_rng(seed)
    starts = pd.date_range("2023-01-01", periods=months, freq="MS")
    weights = np.linspace(1.0, 3.0, months)
    signup = np.sort(rng.choice(months, size=customers, p=weights / weights.sum()))
    rows: list[dict[str, object]] = []
    for n, first in enumerate(signup, start=1):
        states = [int(rng.choice(len(TIERS), p=[0.6, 0.3, 0.1]))]
        for draw in rng.random(months - first - 1):
            states.append(_next_state(states[-1], float(draw)))
        signup_day = starts[first] + pd.Timedelta(days=int(rng.integers(0, 28)))
        for state, lo, hi in _runs(states):
            if state == INACTIVE:
                continue
            begin = signup_day if lo == 0 else starts[first + lo]
            last = first + hi
            rows.append(
                {
                    "customer_id": f"C{n:05d}",
                    "plan": TIERS[state],
                    "monthly_price": PLANS[TIERS[state]],
                    "start_date": begin.strftime("%Y-%m-%d"),
                    "end_date": "" if last == months - 1 else starts[last + 1].strftime("%Y-%m-%d"),
                }
            )
    subs = pd.DataFrame(rows)
    new_counts = np.bincount(signup, minlength=months)
    spend = pd.DataFrame(
        {
            "month": starts.strftime("%Y-%m"),
            "marketing_spend": np.round(new_counts * rng.uniform(70, 130, size=months), 2),
        }
    )
    return subs, spend
