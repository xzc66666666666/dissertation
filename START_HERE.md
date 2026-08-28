# Scheme 5 Reproduction

## Final result

- Factor: `BTC_LONG_5b55989455e686eb_2d`
- Formula: `(x_flow_price_gap*x_close_location) | (x_flow_mean_12*m1_return_efficiency_5) | (x_flow_mean_72*x_return_efficiency_288)`
- Research cost: 5bp per completed round-trip trade

## Recommended sequence

1. Read `README.md` to understand the fixed workflow and external inputs.
2. Review `config.json` to confirm the dates, thresholds, and ranking rules.
3. Review `RESULTS.md` and `reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv`.
4. Review `evidence/validation.json`; all 20 checks for the archived version are PASS.
5. Run `./run_full_scheme5.sh` in a new copy of this directory to reproduce all stages.

## Key evidence

| Purpose | Path |
|---|---|
| Seven-block frozen selection catalogue | `reproduced/frozen_library/frozen_factor_catalog.csv` |
| Scheme 5 ranking of four candidates | `reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv` |
| Final one-factor catalogue | `reproduced/scheme5_final_factor/final_factor_catalog.csv` |
| Two-block assessment metrics | `reproduced/holdout_2fold/holdout_2fold_performance.csv` |
| Completed-trade ledger | `reproduced/holdout_2fold/holdout_trade_ledger.parquet` |
| Validation checks | `evidence/validation.json` |
