"""Command-line interface."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

from saas_metrics import __version__
from saas_metrics.io import load_spend, read_subscriptions
from saas_metrics.metrics import compute_metrics
from saas_metrics.models import DataError, MetricsResult
from saas_metrics.report.markdown import fmt
from saas_metrics.sample_data import generate_sample

app = typer.Typer(help="Turn subscription data into SaaS metrics reports.", add_completion=False)
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
FORMATS = ("md", "html", "json", "csv")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"saas-metrics {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    """SaaS metrics toolkit."""


def _fail(message: str) -> typer.Exit:
    typer.echo(f"Error: {message}", err=True)
    return typer.Exit(1)


def _check_month(value: str | None, option: str) -> None:
    if value is not None and not MONTH.match(value):
        typer.echo(f"Error: {option} must look like YYYY-MM, got {value!r}", err=True)
        raise typer.Exit(2)


def _render(result: MetricsResult, fmt_name: str) -> str:
    return {
        "md": result.to_markdown,
        "html": result.to_html,
        "json": result.to_json,
        "csv": result.to_csv,
    }[fmt_name]()


def _summary(result: MetricsResult) -> str:
    last = result.monthly.iloc[-1]
    lines = [
        f"Months analysed: {len(result.monthly)} ({result.monthly['month'].iloc[0]} to {last['month']})",
        f"MRR: {fmt(last['mrr'], 'money')}   ARR: {fmt(last['arr'], 'money')}",
        f"Active customers: {fmt(last['active_customers'], 'int')}",
        f"NRR: {fmt(last['nrr'], 'rate')}   GRR: {fmt(last['grr'], 'rate')}   Logo churn: {fmt(last['logo_churn_rate'], 'rate')}",
        f"LTV: {fmt(last['ltv'], 'money')}   CAC: {fmt(last['cac'], 'money')}   LTV:CAC: {fmt(last['ltv_cac'], 'ratio')}",
        f"Quick ratio: {fmt(last['quick_ratio'], 'ratio')}",
    ]
    return "\n".join(lines)


@app.command()
def report(
    subscriptions: Annotated[Path, typer.Argument(help="Subscriptions CSV.")],
    spend: Annotated[Path | None, typer.Option(help="Marketing spend CSV, used for CAC.")] = None,
    gross_margin: Annotated[float, typer.Option(help="Gross margin in (0, 1].")] = 0.8,
    format: Annotated[str, typer.Option("--format", help="md, html, json or csv.")] = "md",
    out: Annotated[Path | None, typer.Option(help="Write the full report here.")] = None,
    from_month: Annotated[str | None, typer.Option("--from", help="First month, YYYY-MM.")] = None,
    to_month: Annotated[str | None, typer.Option("--to", help="Last month, YYYY-MM.")] = None,
) -> None:
    """Compute metrics and print a summary; write the full report with --out."""
    if format not in FORMATS:
        typer.echo(f"Error: --format must be one of {', '.join(FORMATS)}", err=True)
        raise typer.Exit(2)
    _check_month(from_month, "--from")
    _check_month(to_month, "--to")
    try:
        subs, rep = read_subscriptions(subscriptions)
        if not rep.ok:
            raise DataError("\n".join(["invalid subscriptions file:", *[f"  - {i}" for i in rep.errors]]))
        for issue in rep.warnings:
            typer.echo(f"Warning: {issue}", err=True)
        spend_df = load_spend(spend) if spend else None
        result = compute_metrics(subs, spend_df, gross_margin).between(from_month, to_month)
        if result.monthly.empty:
            raise DataError("no months fall inside the requested --from/--to range")
        text = _render(result, format)
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
    except DataError as exc:
        raise _fail(str(exc)) from None
    except OSError as exc:
        raise _fail(f"cannot write output: {exc}") from None
    if out is not None:
        typer.echo(_summary(result))
        typer.echo(f"\nReport written to {out}")
    else:
        typer.echo(text)


@app.command()
def validate(subscriptions: Annotated[Path, typer.Argument(help="Subscriptions CSV.")]) -> None:
    """Validate a subscriptions CSV and list problems with row numbers."""
    try:
        df, rep = read_subscriptions(subscriptions)
    except DataError as exc:
        raise _fail(str(exc)) from None
    for issue in rep.warnings:
        typer.echo(f"Warning: {issue}")
    for issue in rep.errors:
        typer.echo(f"Error: {issue}")
    if not rep.ok:
        typer.echo(f"\nInvalid: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s).")
        raise typer.Exit(1)
    typer.echo(f"Valid: {len(df)} rows, {df['customer_id'].nunique()} customers, {len(rep.warnings)} warning(s).")


@app.command()
def sample(
    out: Annotated[Path, typer.Option(help="Output directory.")],
    customers: Annotated[int, typer.Option(min=1, help="Number of customers.")] = 500,
    months: Annotated[int, typer.Option(min=1, help="Number of months.")] = 24,
    seed: Annotated[int, typer.Option(help="Random seed.")] = 42,
) -> None:
    """Generate synthetic subscriptions.csv and spend.csv."""
    subs, spend = generate_sample(customers, months, seed)
    try:
        out.mkdir(parents=True, exist_ok=True)
        subs.to_csv(out / "subscriptions.csv", index=False, lineterminator="\n")
        spend.to_csv(out / "spend.csv", index=False, lineterminator="\n")
    except OSError as exc:
        raise _fail(f"cannot write to {out}: {exc}") from None
    typer.echo(f"Wrote {len(subs)} subscription rows to {out / 'subscriptions.csv'}")
    typer.echo(f"Wrote {len(spend)} spend rows to {out / 'spend.csv'}")
