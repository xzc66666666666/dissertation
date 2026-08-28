# BTCUSDT 5bp Scheme 5 Factor-Mining Reproduction Package

This repository is the code-and-evidence companion to the dissertation's FRPE-2D case study. The research instrument is the Binance BTCUSDT USDT-margined perpetual futures contract. Historical artifact paths containing `spot` are immutable legacy names and do not identify the market used in the calculations.

For the repository boundary and external inputs, see [`REPOSITORY_GUIDE.md`](REPOSITORY_GUIDE.md).

## Final factor

- Factor ID: `BTC_LONG_5b55989455e686eb_2d`
- Formula: `(x_flow_price_gap*x_close_location) | (x_flow_mean_12*m1_return_efficiency_5) | (x_flow_mean_72*x_return_efficiency_288)`
- Instrument: Binance BTCUSDT USDT-M perpetual futures
- Horizon: approximately 48 hours, with no overlapping positions for the factor
- Cost: 5 bp deducted once per completed round trip
- Threshold: monthly `q=99` of absolute score from the preceding 180 calendar days, requiring at least 500 prior events
- Timing: features must be available by `decision_time`; archived entry occurs at least 60 seconds later

The parameter choices are archived reconstruction settings. The archive does not establish that the factor, `q=99`, 180-day window, or 60-second delay were externally registered before the 2025-2026 outcomes were observed. The final period is therefore a historical assessment, not a genuine holdout or out-of-sample test.

## Archived reconstruction workflow

1. Start from the 1,200 exact long-horizon definitions retained by the original 5 bp run.
2. Evaluate seven consecutive 180-day selection blocks from 2022-01-07 inclusive to 2025-06-20 exclusive.
3. Apply stability, core-tier, lineage-overlap, and score-correlation filters to archive a 100-factor catalogue, including 12 core factors.
4. Require core tier, `q=99`, at least six positive selection blocks, and no more than 30% of positive profit from the five largest winners.
5. Rank eligible factors on four equal-weight ordinal criteria and archive rank 1 for the reconstruction.
6. Assess the archived reconstruction factor from 2025-06-20 inclusive to 2026-06-15 exclusive in two report-only 180-day blocks.

## Post-selection diagnostics

`code/audit_assessment_concentration_and_tail.py` records two deliberately separate audits.  It quantifies realised-profit concentration from the 49 completed non-overlapping, 5 bp costed trades, then tests the q=99 rule's directional information on all 87 raw threshold-passing assessment events before overlap selection and costs.  Its JSON output is `evidence/assessment_tail_and_concentration.json`.  These are post-selection historical diagnostics, not prospective confirmation or preregistration evidence.

## Audit findings

- `evidence/usdtm_source_identity.json` verifies all 78 monthly source hashes against official Binance Vision USDT-M Kline checksums. All 78 match.
- The apparent 2,325-minute discrepancy came from comparing separate Binance spot annual files with perpetual-futures data. All 2,325 perpetual rows exist and have positive trade counts; they were not synthetic gap fills.
- `evidence/frpe_snapshot_equivalence.json` compares the discovery and final-selection/MTM snapshots across 49,486 keyed rows, including 7,769 assessment rows.
- The largest six-input difference is `1.145e-12`. Scores, monthly thresholds, 87 raw triggers, 49 completed trades, and every reported performance metric are exactly invariant.
- Four event rows contain a missing value in one of the six inputs (`0.00804%` of 49,773 events). None is in the assessment trigger set; complete-case deletion produces identical thresholds, trades, and performance.

## Reproduction

Run from a clean copy of this directory:

```bash
./run_full_scheme5.sh
```

The runner relies on the external full-chain bundle for the large event-feature snapshot, retained candidate specifications, original miner, and Python environment. It does not regenerate the one-million-candidate search and stops if output directories already exist.

## Contents

| Path | Purpose |
|---|---|
| `START_HERE.md` | Recommended review sequence |
| `STRATEGY_SPEC.md` | Factor, feature, event, timing, and accounting contract |
| `code/` | Selection, assessment, validation, and audit scripts |
| `reproduced/` | Archived catalogues, rankings, metrics, and trade ledgers |
| `evidence/` | Experiment summary, validation, feature contract, and new audits |
| `RESULTS.md` | Results and evidential interpretation |
| `PACKAGE_MANIFEST.md` | Package contents and external-input boundary |

## Research status

This is a historical research candidate, not evidence of validated alpha or an investment recommendation. The package does not establish real fills, independent market impact, live latency, funding costs, capacity, paper trading, or production risk controls.
