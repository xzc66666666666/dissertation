# Package Manifest

## Package identity

- Package directory: `btc_factor_scheme5_factor_mining_package_20260823`
- Experiment identifier: `btc_cost5_scheme5_frozen_selection_20260822_v1`
- Cost convention: 5bp deducted for each completed round-trip trade
- Final factor: `BTC_LONG_5b55989455e686eb_2d`

## Code entry points

1. `code/build_selection_7fold.py`: generates seven selection blocks using the fixed 1,200 definitions.
2. `code/finalize_selection_7fold.py`: applies the stable/core thresholds, de-duplicates candidates, and writes the 100-factor frozen catalogue.
3. `code/select_scheme5_final_factor.py`: applies the Scheme 5 thresholds and ranks eligible candidates.
4. `code/evaluate_holdout_2fold.py`: runs the frozen factor across two staged assessment blocks.
5. `code/build_scheme5_summary.py` and `code/validate_scheme5_outputs.py`: generate the summary and validate archived artifacts.
6. `STRATEGY_SPEC.md`: a one-page specification of the final factor, selection thresholds, execution convention, and reproduced results.

## Inputs required for a full rerun

- A long-horizon event-feature snapshot;
- The 1,200 factor definitions and candidate specifications retained by the original 5bp run;
- Original causal rolling-audit artifacts for historical-prefix consistency checks;
- A Python environment containing NumPy, pandas, and PyArrow.

See `run_full_scheme5.sh` for the default paths. They can be overridden through environment variables with the same names.

## Archive checks

`evidence/validation.json` records the results of 20 checks covering the frozen catalogue, Scheme 5 ranking, catalogue membership, time boundaries, cost convention, and historical-ledger consistency.
