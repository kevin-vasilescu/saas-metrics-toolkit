"""CLI tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from saas_metrics import __version__
from saas_metrics.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_sample_then_report(tmp_path: Path) -> None:
    out = tmp_path / "data"
    assert runner.invoke(app, ["sample", "--customers", "40", "--months", "8", "--out", str(out)]).exit_code == 0
    assert (out / "subscriptions.csv").exists()
    result = runner.invoke(
        app, ["report", str(out / "subscriptions.csv"), "--spend", str(out / "spend.csv")]
    )
    assert result.exit_code == 0
    assert "# SaaS Metrics Report" in result.output


def test_report_writes_each_format(tmp_path: Path, fixtures_dir: Path) -> None:
    subs = str(fixtures_dir / "basic_subscriptions.csv")
    for fmt, marker in (("md", "# SaaS"), ("html", "<!DOCTYPE"), ("json", '"monthly"'), ("csv", "month,mrr")):
        target = tmp_path / f"r.{fmt}"
        result = runner.invoke(app, ["report", subs, "--format", fmt, "--out", str(target)])
        assert result.exit_code == 0, result.output
        assert marker in target.read_text(encoding="utf-8")
        assert "Report written to" in result.output


def test_report_range(fixtures_dir: Path) -> None:
    result = runner.invoke(
        app, ["report", str(fixtures_dir / "basic_subscriptions.csv"), "--from", "2024-03", "--format", "csv"]
    )
    assert result.exit_code == 0
    assert "2024-02" not in result.output
    assert "2024-04" in result.output


def test_report_empty_range(fixtures_dir: Path) -> None:
    result = runner.invoke(app, ["report", str(fixtures_dir / "basic_subscriptions.csv"), "--from", "2030-01"])
    assert result.exit_code == 1
    assert "no months" in result.output


def test_usage_errors(fixtures_dir: Path) -> None:
    subs = str(fixtures_dir / "basic_subscriptions.csv")
    assert runner.invoke(app, ["report", subs, "--format", "pdf"]).exit_code == 2
    assert runner.invoke(app, ["report", subs, "--from", "2024/01"]).exit_code == 2
    assert runner.invoke(app, ["report"]).exit_code == 2
    assert runner.invoke(app, ["nonsense"]).exit_code == 2


def test_missing_file_is_friendly(tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", str(tmp_path / "x.csv")])
    assert result.exit_code == 1
    assert "file not found" in result.output
    assert "Traceback" not in result.output


def test_bad_gross_margin(fixtures_dir: Path) -> None:
    result = runner.invoke(app, ["report", str(fixtures_dir / "basic_subscriptions.csv"), "--gross-margin", "2"])
    assert result.exit_code == 1
    assert "gross_margin" in result.output


def test_bad_spend_file(tmp_path: Path, fixtures_dir: Path) -> None:
    spend = tmp_path / "s.csv"
    spend.write_text("month,marketing_spend\nxx,1\n")
    result = runner.invoke(app, ["report", str(fixtures_dir / "basic_subscriptions.csv"), "--spend", str(spend)])
    assert result.exit_code == 1


def test_report_invalid_subscriptions_lists_rows(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("customer_id,plan,monthly_price,start_date,end_date\n,p,5,2024-01-01,\n")
    result = runner.invoke(app, ["report", str(bad)])
    assert result.exit_code == 1
    assert "row 2" in result.output


def test_report_shows_warnings(tmp_path: Path) -> None:
    path = tmp_path / "dup.csv"
    row = "a,p,5,2024-01-01,\n"
    path.write_text("customer_id,plan,monthly_price,start_date,end_date\n" + row + row)
    result = runner.invoke(app, ["report", str(path)])
    assert result.exit_code == 0
    assert "duplicate row dropped" in result.output


def test_validate_ok_and_failure(tmp_path: Path, fixtures_dir: Path) -> None:
    ok = runner.invoke(app, ["validate", str(fixtures_dir / "basic_subscriptions.csv")])
    assert ok.exit_code == 0
    assert "Valid: 6 rows, 4 customers" in ok.output
    bad = tmp_path / "bad.csv"
    bad.write_text("customer_id,plan,monthly_price,start_date,end_date\na,p,5,2024-02-01,2024-01-01\n")
    result = runner.invoke(app, ["validate", str(bad)])
    assert result.exit_code == 1
    assert "row 2: end_date is before start_date" in result.output
    assert runner.invoke(app, ["validate", str(tmp_path / "none.csv")]).exit_code == 1


def test_output_dir_unwritable(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    result = runner.invoke(app, ["sample", "--out", str(blocker / "sub")])
    assert result.exit_code == 1
    assert "cannot write" in result.output


def test_report_output_unwritable(tmp_path: Path, fixtures_dir: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    result = runner.invoke(
        app, ["report", str(fixtures_dir / "basic_subscriptions.csv"), "--out", str(blocker / "r.md")]
    )
    assert result.exit_code == 1
