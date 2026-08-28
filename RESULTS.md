# BTCUSDT 5bp Scheme 5 Reproduction Results

## Factor selection funnel

| Stage | Factor count |
|---|---:|
| Exact retained candidate definitions | 1,200 |
| Development candidates | 849 |
| Passed seven-block stability threshold | 179 |
| Passed seven-block core threshold | 19 |
| Frozen catalogue after de-duplication | 100 |
| Core factors in frozen catalogue | 12 |
| Passed Scheme 5 baseline criteria | 4 |
| Final frozen factor | 1 |

The final factor is `BTC_LONG_5b55989455e686eb_2d` for Binance BTCUSDT USDT-M perpetual futures.

## Scheme 5 candidate ranking

| Factor | Signal redundancy | CAGR gap | Mean gross trade-return gap | Selection trades | Rank sum | Final rank |
|---|---:|---:|---:|---:|---:|---:|
| `BTC_LONG_5b55989455e686eb_2d` | 0.0723 | 18.74 pp | 96.79 bp | 178 | 4 | 1 |
| `BTC_LONG_546aae11ff7d6499_2d` | 0.1149 | 19.32 pp | 112.10 bp | 92 | 11 | 2 |
| `BTC_LONG_8a7646dc5ccbd0f9_1d` | 0.1287 | 20.50 pp | 124.94 bp | 152 | 12 | 3 |
| `BTC_LONG_6e133e86c2c01d4b_3d` | 0.0937 | 60.98 pp | 214.81 bp | 131 | 13 | 4 |

## Historical assessment after freezing

| Metric | Result |
|---|---:|
| Completed trades | 49 |
| CAGR | 23.3323% |
| Sharpe | 1.0693 |
| Maximum drawdown | -11.4160% |
| Calmar | 2.0438 |
| First 180-day block net-return sum | 2.51% |
| Second 180-day block net-return sum | 20.54% |
| Positive-return blocks | 2 / 2 |

Approximately 97.3% of the two-block net-return sum is concentrated in the second block. Assessment rank IC is `-0.0176`; bootstrap intervals cross zero and the reported placebo p-values exceed 0.05. The present assessment does not furnish affirmative evidence for conditional directional information. The positive realised outcome is compatible with H2, but the available evidence is insufficient to establish positive expected net performance. The evidence does not permit the temporal component of H3 to be affirmed, given the concentration of gains in the later block. The attractive aggregate performance should therefore be treated as descriptive historical evidence.

The archive does not establish that the factor and its evaluation settings were fixed before the 2025-2026 outcomes were observed. Accordingly, this period is called a historical assessment, not a genuine holdout or out-of-sample test. Legacy directory and column names containing `holdout` are preserved only for artifact compatibility.

## Snapshot-equivalence audit

The discovery snapshot (`45e9d44e...`) and final-selection/MTM snapshot (`8d93f3ea...`) have different binary hashes. A keyed recomputation nevertheless establishes:

| Audit item | Result |
|---|---:|
| Rows compared | 49,486 |
| Assessment rows | 7,769 |
| Largest six-input absolute difference | `1.145e-12` |
| Score maximum difference | 0 |
| Monthly q=99 threshold maximum difference | 0 |
| Raw triggers | 87 vs 87; symmetric difference 0 |
| Completed trades | 49 vs 49; identical event IDs and timestamps |
| Net-return maximum difference | 0 |
| All performance-metric differences | 0 |

The complete machine-readable comparison is in `evidence/frpe_snapshot_equivalence.json`. The different file hashes do not alter the frozen reconstruction's economic output.

## Data-source and missingness audits

`evidence/usdtm_source_identity.json` verifies 78/78 monthly embedded source hashes against official Binance Vision USDT-M Futures BTCUSDT one-minute Kline ZIP checksums. The previously reported 2,325-minute discrepancy is a cross-market comparison: those timestamps are absent from separately supplied spot annual files but are present in the perpetual-futures source. Every one of the 2,325 futures rows has a positive trade count.

Among all 49,773 events, four rows (`0.00804%`) contain a missing value in one of the six FRPE inputs. None is an assessment trigger. Removing incomplete rows rather than applying the archived post-standardisation zero treatment leaves thresholds, 87 triggers, 49 trades, and all return-risk metrics unchanged.

## Accounting boundary

Each completed trade is charged 5 bp. Sharpe and maximum drawdown use exit-date realised-P&L accounting rather than daily mark-to-market while positions are open. The archived entry price is a research label endpoint, not evidence of a contemporaneously executable fill. Funding, liquidation, bid-ask spread beyond the fixed cost, independent market impact, and live controls are not modelled.
