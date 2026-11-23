# Usage

## Validate first

```bash
saas-metrics validate subscriptions.csv
```

Prints each problem as `row N: message`. Warnings (duplicates, overlaps) do not fail validation.

## Reports

```bash
saas-metrics report subscriptions.csv --spend spend.csv --format html --out report.html
saas-metrics report subscriptions.csv --from 2024-01 --to 2024-06 --format json --out h1.json
saas-metrics report subscriptions.csv --gross-margin 0.75
```

Without `--out` the full report prints to the terminal. With `--out` a short summary prints and the report is written to the file. `--from` and `--to` restrict the monthly table; cohort retention always uses all data.

## Output schemas

JSON has the keys `gross_margin`, `monthly` (list of records) and `cohorts` (list of records). CSV contains the monthly table. Undefined values are `null` in JSON and empty in CSV.

## Python

```python
from saas_metrics import load_subscriptions, compute_metrics

result = compute_metrics(load_subscriptions("subscriptions.csv"))
result.to_dataframe()
```

Expected errors raise `saas_metrics.DataError`.
