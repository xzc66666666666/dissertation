# BTCUSDT 5bp Scheme 5 Reproduction Results

## Factor selection funnel

| Stage | Factor count |
|---|---:|
| Exact candidate definitions | 1,200 |
| Development candidates | 849 |
| Passed seven-block stability threshold | 179 |
| Passed seven-block core threshold | 19 |
| Frozen catalogue after de-duplication | 100 |
| Core factors among them | 12 |
| Passed Scheme 5 baseline criteria | 4 |
| Scheme 5 final frozen factor | 1 |

The final factor is `BTC_LONG_5b55989455e686eb_2d`.

## Scheme 5 candidate ranking

| Factor | Signal redundancy | CAGR gap | Mean gross trade return gap | Seven-block trade count | Rank sum | Final rank |
|---|---:|---:|---:|---:|---:|---:|
| `BTC_LONG_5b55989455e686eb_2d` | 0.0723 | 18.74pp | 96.79bp | 178 | 4 | 1 |
| `BTC_LONG_546aae11ff7d6499_2d` | 0.1149 | 19.32pp | 112.10bp | 92 | 11 | 2 |
| `BTC_LONG_8a7646dc5ccbd0f9_1d` | 0.1287 | 20.50pp | 124.94bp | 152 | 12 | 3 |
| `BTC_LONG_6e133e86c2c01d4b_3d` | 0.0937 | 60.98pp | 214.81bp | 131 | 13 | 4 |

## Two-block assessment after freezing

| Metric | Result |
|---|---:|
| Trade count | 49 |
| CAGR | 23.33% |
| Sharpe | 1.069 |
| Maximum drawdown | -11.42% |
| Calmar | 2.044 |
| Block 1 net return sum | 2.51% |
| Block 2 net return sum | 20.54% |
| Positive-return blocks | 2 / 2 |

Each completed trade is charged 5bp. The performance ledger is booked on the exit date of each completed trade; therefore, Sharpe and maximum drawdown use exit-date accounting rather than daily mark-to-market accounting while positions are open.

## Validation status

All checks in `evidence/validation.json` are PASS: the factor definitions, development-period quantiles, development-period metrics, and seven-block trade ledger are consistent with the original 5bp historical prefix. The final catalogue is fixed as the Scheme 5 rank-1 factor, with a 5bp cost convention.
