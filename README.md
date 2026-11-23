# saas-metrics-toolkit

Turn raw subscription data into MRR, churn, NRR, LTV/CAC, and cohort retention reports in one command.

[![CI](https://github.com/kevin-vasilescu/saas-metrics-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kevin-vasilescu/saas-metrics-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/kevin-vasilescu/saas-metrics-toolkit)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)

## Why this exists

Founders, finance and RevOps people at small SaaS companies usually have one thing: a CSV export from Stripe or a billing tool. Getting trustworthy MRR, churn and retention numbers from it normally means a BI tool or a fragile spreadsheet. This toolkit computes the standard metrics from that export with documented formulas, handles messy data (reactivations, plan changes, duplicates) and never emits NaN or infinity.

## Features

- Monthly MRR, ARR, new, expansion, contraction and churned MRR
- Logo churn, gross revenue churn, NRR, GRR, ARPA, LTV, CAC, CAC payback, LTV:CAC and Quick Ratio
- Cohort retention matrix
- Row-numbered input validation
- Reports as Markdown, self-contained HTML (inline CSS and SVG chart, no external requests), JSON and CSV
- Deterministic synthetic data generator
- Python API and a Typer CLI

## Installation

```bash
pip install git+https://github.com/kevin-vasilescu/saas-metrics-toolkit.git
```

From source:

```bash
git clone https://github.com/kevin-vasilescu/saas-metrics-toolkit.git
cd saas-metrics-toolkit
pip install .
```

## 60-second quickstart

Output captured from a real run of these commands:

```console
$ saas-metrics sample --customers 80 --months 12 --out examples
Wrote 91 subscription rows to examples/subscriptions.csv
Wrote 12 spend rows to examples/spend.csv

$ saas-metrics report examples/subscriptions.csv --spend examples/spend.csv --out examples/report.md
Months analysed: 12 (2023-01 to 2023-12)
MRR: 4,171.00   ARR: 50,052.00
Active customers: 69
NRR: 97.3%   GRR: 97.3%   Logo churn: 3.1%
LTV: 1,571.68   CAC: 96.10   LTV:CAC: 16.35x
Quick ratio: 3.00x

Report written to examples/report.md
```

The sample data is deterministic, so the same seed reproduces these numbers. Use `--format html` for the HTML report.

## Python API

```python
from saas_metrics import load_subscriptions, load_spend, compute_metrics, cohort_retention

subs = load_subscriptions("examples/subscriptions.csv")
spend = load_spend("examples/spend.csv")
result = compute_metrics(subs, spend, gross_margin=0.8)

print(result.to_dataframe().tail(1).T)   # missing values are None
print(cohort_retention(subs).head())
html = result.to_html()                  # also: to_json(), to_markdown()
```

## CLI reference

| Command | Description |
|---|---|
| `saas-metrics report SUBSCRIPTIONS_CSV` | Print a summary; write the full report with `--out`. Options: `--spend`, `--gross-margin` (default 0.8), `--format md\|html\|json\|csv`, `--from YYYY-MM`, `--to YYYY-MM` |
| `saas-metrics validate SUBSCRIPTIONS_CSV` | List errors and warnings with row numbers |
| `saas-metrics sample --out DIR` | Generate `subscriptions.csv` and `spend.csv`. Options: `--customers 500`, `--months 24`, `--seed 42` |
| `saas-metrics --version` | Print the version |

Exit codes: 0 success, 1 data or validation error, 2 usage error.

## Input format

`subscriptions.csv` (required), one row per subscription period. A customer can have many rows.

| Column | Type | Notes |
|---|---|---|
| customer_id | text | Not empty |
| plan | text | |
| monthly_price | number | 0 or more |
| start_date | YYYY-MM-DD | |
| end_date | YYYY-MM-DD | Empty means still active |

`spend.csv` (optional, for CAC): `month` (YYYY-MM) and `marketing_spend` (number).

Errors (missing columns, empty file, bad dates, end before start, bad price, empty customer_id) stop the run with row numbers. Overlapping rows on the same plan produce a warning; exact duplicate rows are dropped with a warning.

## Metrics

MRR, ARR, new/expansion/contraction/churned MRR, churn rates, NRR, GRR, ARPA, LTV, CAC, payback, LTV:CAC, Quick Ratio and cohort retention are defined with worked examples in [docs/metrics.md](docs/metrics.md). Reactivations count as new MRR. Any division by zero yields `None` (`n/a` in reports).

## Report preview

Excerpt of the Markdown report from the quickstart run:

```markdown
# SaaS Metrics Report

Period: 2023-01 to 2023-12 (12 months). Gross margin: 80%.

## Key metrics: 2023-12 vs previous month

| Metric | 2023-12 | Previous | Change |
|---|---:|---:|---:|
| MRR | 4,171.00 | 3,955.00 | +216.00 |
| ARR | 50,052.00 | 47,460.00 | +2,592.00 |
| Active customers | 69 | 65 | +4 |
| New MRR | 324.00 | 1,204.00 | -880.00 |
| Churned MRR | 108.00 | 257.00 | -149.00 |
| Expansion MRR | 0.00 | 120.00 | -120.00 |
| Contraction MRR | 0.00 | 240.00 | -240.00 |
| NRR | 97.3% | 87.9% | +9.3 pp |
| GRR | 97.3% | 84.1% | +13.2 pp |
| Logo churn | 3.1% | 5.8% | -2.7 pp |
| ARPA | 60.45 | 60.85 | -0.40 |
| LTV | 1,571.68 | 843.73 | +727.95 |
| CAC | 96.10 | 74.80 | +21.30 |
| CAC payback (months) | 2.2 | 1.2 | +1.0 |
| LTV:CAC | 16.35x | 11.28x | +5.08x |
| Quick ratio | 3.00x | 2.66x | +0.34x |
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
make test
```

`make lint` runs ruff and mypy; `make check` runs everything CI runs.

## Roadmap

- Revenue by plan and segment breakdowns
- Direct Stripe export column mapping
- Annual and quarterly aggregation
- Multi-currency support
- Excel output

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT, see [LICENSE](LICENSE).
