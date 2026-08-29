# BTCUSDT FRPE-2D Retrospective Audit Results

These results belong to a **partial retrospective reconstruction of the retained search trail**. The public repository supports downstream code, ledger, and audit inspection. It does not contain the original 20,000-stage ledger, complete candidate payoff matrix, original one-million-candidate miner, retained-definition input archive, or material upstream feature snapshots, and therefore cannot independently reproduce why FRPE-2D was selected from the full search.

## Factor selection funnel

| Stage | Factor count |
|---|---:|
| Exact retained candidate definitions | 1,200 |
| Development candidates | 849 |
| Passed seven-block stability threshold | 179 |
| Passed seven-block core threshold | 19 |
| Archived catalogue after de-duplication | 100 |
| Core factors in archived catalogue | 12 |
| Passed Scheme 5 baseline criteria | 4 |
| Final archived reconstruction factor | 1 |

The final factor is `BTC_LONG_5b55989455e686eb_2d` for Binance BTCUSDT USDT-M perpetual futures.

## Scheme 5 candidate ranking

| Factor | Signal redundancy | CAGR gap | Mean gross trade-return gap | Selection trades | Rank sum | Final rank |
|---|---:|---:|---:|---:|---:|---:|
| `BTC_LONG_5b55989455e686eb_2d` | 0.0723 | 18.74 pp | 96.79 bp | 178 | 4 | 1 |
| `BTC_LONG_546aae11ff7d6499_2d` | 0.1149 | 19.32 pp | 112.10 bp | 92 | 11 | 2 |
| `BTC_LONG_8a7646dc5ccbd0f9_1d` | 0.1287 | 20.50 pp | 124.94 bp | 152 | 12 | 3 |
| `BTC_LONG_6e133e86c2c01d4b_3d` | 0.0937 | 60.98 pp | 214.81 bp | 131 | 13 | 4 |

## Historical assessment of the archived reconstruction

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

Approximately 97.3% of the two-block net-return sum is concentrated in the second block. Assessment rank IC is `-0.0176`; bootstrap intervals cross zero and the reported placebo p-values exceed 0.05. The present assessment does not furnish affirmative evidence for conditional directional information. The positive realised outcome is compatible with H2, but the available evidence is insufficient to establish positive expected net performance. The evidence does not permit temporal or trade-level concentration robustness to be affirmed. The attractive aggregate performance should therefore be treated as descriptive historical evidence.

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

The complete machine-readable comparison is in `evidence/frpe_snapshot_equivalence.json`. The different file hashes do not alter the archived-reconstruction economic output.

## Assessment tail and concentration audit

`evidence/assessment_tail_and_concentration.json` quantifies the previously unreported trade-level concentration on the 49 completed non-overlapping, 5 bp costed trades. The baseline compounded return is `22.9611%`. The largest winner is `6.4617%`, or `9.4164%` of gross positive trade returns; the top five total `24.6088%`, or `35.8611%`. Removing the largest winner leaves a `15.4979%` compounded return, `15.7409%` CAGR, and `-11.4160%` MDD. Removing the five largest winners leaves `-3.2729%`, `-3.3198%` CAGR, and `-14.6186%` MDD. Thus, the top-five deletion reverses the compounded outcome, so the archived assessment does not affirm trade-level concentration robustness.

Monthly exit-date realised P&L is also uneven: the largest positive months are 2025-09 (`+7.3086%`, six trades), 2025-06 (`+6.0471%`, two trades), 2026-06 (`+5.8666%`, one trade), and 2026-03 (`+5.4180%`, four trades); the largest negative months are 2025-11 (`-4.3707%`) and 2025-12 (`-3.7358%`). This is an accounting-date concentration diagnostic, not a post-hoc market-state classification.

The same evidence file directly tests the q=99 rule on 87 raw threshold-passing assessment events before non-overlap selection and 5 bp costs. The overall directional hit rate is `54.023%` (47/87; 95% Wilson interval `43.603%` to `64.103%`) and mean gross directional return is `0.1135%`. Long triggers show `65.854%` hits and `+0.3436%` mean directional return (41 events), whereas short triggers show `43.478%` hits and `-0.0915%` (46 events). Absolute-score quartiles have non-monotonic mean returns (`+0.6510%`, `-0.5180%`, `+0.0638%`, and `+0.2551%`), and no hit-rate interval excludes 50%. The full-event rank IC is therefore a supplementary ordering diagnostic, while the direct tail test also provides insufficiently precise evidence of conditional directional information.

## Direction attribution and timing-matched long benchmark

`evidence/assessment_direction_attribution.json` is computed from the public 49-trade ledger alone. Direction is `sign(score)`. Long-only and short-only variants retain their respective archived trades and remain flat otherwise. The timing-matched benchmark takes a long BTCUSDT position over every one of the same 49 archived entry/exit intervals and applies the same 5 bp cost. Its endpoint return is algebraically recovered from the archived accounting identity, so this remains a research-accounting comparison rather than an executable-fill test.

| Variant | Trades | Net hit rate (95% Wilson CI) | Arithmetic net-return sum | Share of baseline arithmetic sum | Compounded return | CAGR | MDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full directional rule | 49 | 63.3% (49.3%-75.3%) | +23.05% | 100.0% | +22.96% | +23.33% | -11.42% |
| Long-only; flat otherwise | 28 | 71.4% (52.9%-84.7%) | +13.95% | 60.5% | +13.06% | +13.26% | -10.87% |
| Short-only; flat otherwise | 21 | 52.4% (32.4%-71.7%) | +9.10% | 39.5% | +8.76% | +8.89% | -7.08% |
| Timing-matched all-long | 49 | 61.2% (47.2%-73.6%) | +2.76% | n.a. | +0.37% | +0.37% | -16.80% |

The raw trigger pool is materially long-favouring, but the final completed ledger is not explained by uniform long exposure alone: both archived direction subsets contribute positively, while the same-timing all-long benchmark is near flat and has a deeper drawdown. This is a descriptive post-selection contrast. It neither establishes stable bidirectional information nor eliminates regime dependence, non-overlap selection effects, or winner-selection uncertainty.

## Data-source and missingness audits

`evidence/usdtm_source_identity.json` verifies 78/78 monthly embedded source hashes against official Binance Vision USDT-M Futures BTCUSDT one-minute Kline ZIP checksums. The previously reported 2,325-minute discrepancy is a cross-market comparison: those timestamps are absent from separately supplied spot annual files but are present in the perpetual-futures source. Every one of the 2,325 futures rows has a positive trade count.

Among all 49,773 events, four rows (`0.00804%`) contain a missing value in one of the six FRPE inputs. None is an assessment trigger. Removing incomplete rows rather than applying the archived post-standardisation zero treatment leaves thresholds, 87 triggers, 49 trades, and all return-risk metrics unchanged.

## Accounting boundary

Each completed trade is charged 5 bp. Sharpe and maximum drawdown use exit-date realised-P&L accounting rather than daily mark-to-market while positions are open. The archived entry price is a research label endpoint, not evidence of a contemporaneously executable fill. Funding, liquidation, bid-ask spread beyond the fixed cost, independent market impact, and live controls are not modelled.
