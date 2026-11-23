# Metric reference

All metrics are computed per calendar month. A subscription row is active in a month if `start_date <= month_end` and `end_date` is empty or `end_date > month_end`. A customer's MRR in a month is the sum of the prices of their active rows. Each month is compared with the previous month; the first month compares with zero. Any division by zero returns `None`.

| Metric | Formula |
|---|---|
| MRR | sum of customer MRR at month end |
| ARR | MRR x 12 |
| New MRR | current MRR of customers with previous MRR = 0 and current > 0. Reactivations count as new |
| Churned MRR | previous MRR of customers with previous > 0 and current = 0 |
| Expansion MRR | current - previous where both > 0 and current > previous |
| Contraction MRR | previous - current (positive) where both > 0 and current < previous |
| Logo churn rate | churned customers / customers at start of month |
| Gross revenue churn rate | (churned + contraction MRR) / starting MRR |
| NRR | (starting MRR + expansion - contraction - churned) / starting MRR |
| GRR | (starting MRR - contraction - churned) / starting MRR |
| ARPA | MRR / active customers |
| LTV | ARPA x gross margin / logo churn rate (None if churn is 0) |
| CAC | marketing spend / new customers (None without spend or new customers) |
| CAC payback (months) | CAC / (new-customer ARPA x gross margin), where new-customer ARPA = new MRR / new customers |
| LTV:CAC | LTV / CAC |
| Quick ratio | (new + expansion MRR) / (churned + contraction MRR) |
| Cohort retention | cohort = month of a customer's first start_date; value = % of cohort with MRR > 0 N months later |

Gross margin defaults to 0.80 and must be in (0, 1].

## Worked example

Customers A (100/month from January, still active), B (50, ends 2024-03-01), C (30 from February, upgrades to 80 on 2024-03-01), D (40, ends 2024-02-15).

- January MRR: 100 + 50 + 40 = 190. February: 100 + 50 + 30 = 180, with D churned (40) and C new (30).
- February logo churn: 1 / 3. NRR: (190 - 40) / 190 = 78.9%.
- March MRR: 100 + 80 = 180. B churned (50), C expanded by 50. NRR: (180 + 50 - 0 - 50) / 180 = 100%. GRR: (180 - 50) / 180 = 72.2%. Quick ratio: 50 / 50 = 1.0.
- March ARPA: 180 / 2 = 90. LTV: 90 x 0.8 / (1/3) = 216.

These numbers are asserted in `tests/test_metrics.py`.
