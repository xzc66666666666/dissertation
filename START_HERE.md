# Start Here

## Final research object

- Instrument: Binance BTCUSDT USDT-M perpetual futures
- Factor: `BTC_LONG_5b55989455e686eb_2d`
- Formula: `(x_flow_price_gap*x_close_location) | (x_flow_mean_12*m1_return_efficiency_5) | (x_flow_mean_72*x_return_efficiency_288)`
- Research cost: 5 bp per completed round trip
- Evidential status: historical assessment, not a genuine holdout or out-of-sample test

## Recommended review sequence

1. Read `README.md` for the scope, workflow, and research limits.
2. Read `STRATEGY_SPEC.md` for the market, event, feature, timestamp, and accounting definitions.
3. Inspect `evidence/frpe_feature_contract.json` for the machine-readable six-input contract.
4. Inspect `evidence/usdtm_source_identity.json` for the 78-month official source-hash audit and the resolution of the 2,325-minute cross-market discrepancy.
5. Inspect `evidence/frpe_snapshot_equivalence.json` for the keyed discovery-versus-final snapshot comparison.
6. Read `RESULTS.md` and inspect `reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv`.
7. Review `evidence/validation.json`; the archived workflow checks are PASS.
8. Run `./run_full_scheme5.sh` in a clean package copy when the external full-chain inputs are available.

## Key evidence

| Purpose | Path |
|---|---|
| Seven-block frozen catalogue | `reproduced/frozen_library/frozen_factor_catalog.csv` |
| Scheme 5 ranking | `reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv` |
| Final one-factor catalogue | `reproduced/scheme5_final_factor/final_factor_catalog.csv` |
| Historical assessment metrics | `reproduced/holdout_2fold/holdout_2fold_performance.csv` |
| Completed-trade ledger | `reproduced/holdout_2fold/holdout_trade_ledger.parquet` |
| FRPE feature definitions | `evidence/frpe_feature_contract.json` |
| Snapshot-equivalence audit | `evidence/frpe_snapshot_equivalence.json` |
| USDT-M source-identity audit | `evidence/usdtm_source_identity.json` |
| Archived workflow checks | `evidence/validation.json` |

Names containing `spot` or `holdout` are retained legacy artifact names. They do not change the verified USDT-M perpetual-futures market identity or confer prospective out-of-sample status.
