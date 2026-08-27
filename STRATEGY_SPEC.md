# Scheme 5 Strategy Specification

## Frozen strategy

- Factor ID: `BTC_LONG_5b55989455e686eb_2d`
- Horizon: `2d` (approximately 48 hours maximum holding time)
- Cost: 5 bp per completed round trip
- Position rule: non-overlapping positions for the same factor
- Threshold: rolling absolute-score quantile `q=99`
- Final score orientation: `-1`

## Formula

```text
(x_flow_price_gap*x_close_location)
| (x_flow_mean_12*m1_return_efficiency_5)
| (x_flow_mean_72*x_return_efficiency_288)
```

The stored component weights are `0.5`, `-1`, and `-0.5`. The vertical bar is the package's additive component separator.

## Selection procedure

1. Start from the frozen 1,200 exact long-horizon factor definitions.
2. Evaluate seven consecutive 180-day selection blocks from 2022-01-07 inclusive to 2025-06-20 exclusive.
3. Keep the stable tier when at least 5 of 7 blocks are positive; keep the core tier when at least 6 of 7 are positive.
4. Apply feature-lineage and score-correlation de-duplication to form a 100-factor frozen catalogue, including 12 core factors.
5. Apply Scheme 5 eligibility: core tier, `q=99`, at least 6 positive blocks, and top-five winning-profit contribution no greater than 30%.
6. Rank eligible candidates by equal ordinal weight on redundancy, CAGR gap, gross-bp gap, and selection trade count. Freeze rank 1.

## Execution accounting

At each event, compare the oriented score with the rolling threshold. Open a long or short position only when the corresponding threshold is crossed and no position is open. Enter at the next executable event price, exit at the two-day horizon, and deduct 5 bp once from the completed trade. Book realised P&L on the exit timestamp.

## Reproduced result

- Exact candidates: 1,200
- Development candidates: 849
- Stable gate: 179
- Core gate: 19
- Frozen catalogue: 100
- Frozen core: 12
- Scheme 5 eligible: 4
- Final factor: `BTC_LONG_5b55989455e686eb_2d`
- Assessment trades: 49
- Assessment CAGR: 23.33%
- Assessment Sharpe: 1.069
- Assessment maximum drawdown: -11.42%
- Assessment Calmar: 2.044

## Reproduction entry point

Run `./run_full_scheme5.sh` in a clean copy of this package. The runner uses the adjacent verified full-chain bundle for the long-horizon feature snapshot, the retained factor definitions, and the Python environment. It does not regenerate the million-candidate search.
