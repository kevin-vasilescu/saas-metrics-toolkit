"""Report rendering tests."""

from __future__ import annotations

import json

import pandas as pd

from saas_metrics import compute_metrics
from saas_metrics.report.charts import line_chart


def test_markdown_sections(basic_subs: pd.DataFrame, basic_spend: pd.DataFrame) -> None:
    md = compute_metrics(basic_subs, basic_spend).to_markdown()
    for heading in ("# SaaS Metrics Report", "## Key metrics", "## Monthly metrics", "## Cohort retention"):
        assert heading in md
    assert "| MRR | 220.00 | 180.00 | +40.00 |" in md
    assert "NaN" not in md
    assert "n/a" in md


def test_html_is_self_contained(basic_subs: pd.DataFrame) -> None:
    html = compute_metrics(basic_subs).to_html()
    assert html.startswith("<!DOCTYPE html>")
    assert "<svg" in html
    assert "background:rgba(" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html


def test_json_schema_is_stable(basic_subs: pd.DataFrame) -> None:
    data = json.loads(compute_metrics(basic_subs).to_json())
    assert set(data) == {"gross_margin", "monthly", "cohorts"}
    assert list(data["monthly"][0])[:3] == ["month", "mrr", "arr"]
    assert data["cohorts"][0]["cohort"] == "2024-01"


def test_csv_has_header_and_rows(basic_subs: pd.DataFrame) -> None:
    lines = compute_metrics(basic_subs).to_csv().strip().splitlines()
    assert lines[0].startswith("month,mrr,arr")
    assert len(lines) == 5


def test_single_month_report(basic_subs: pd.DataFrame) -> None:
    result = compute_metrics(basic_subs).between("2024-01", "2024-01")
    assert "n/a" in result.to_markdown()
    assert "<svg" in result.to_html()


def test_chart_edge_cases() -> None:
    assert line_chart([], []) == ""
    assert "<polyline" in line_chart(["2024-01"], [5.0])
    assert "&lt;" in line_chart(["<x>"], [1.0, 2.0][:1])
