# BTCUSDT 5bp Scheme 5 Factor-Mining Reproduction Package

For GitHub publication and repository-specific setup notes, see
[`REPOSITORY_GUIDE.md`](REPOSITORY_GUIDE.md). The guide records the exact
reproduction boundary and the inputs that are intentionally kept outside this
repository.

This is an isolated packaging of the Scheme 5 factor-mining workflow, archived as `btc_factor_scheme5_factor_mining_package_20260823`. It does not overwrite the existing 5bp, 20bp, or 30bp research packages. The underlying experiment identifier is `btc_cost5_scheme5_frozen_selection_20260822_v1`.

## Scope

- Asset: BTCUSDT spot event data.
- Candidate definitions: the 1,200 exact long-horizon factors retained by the original 5bp run.
- Cost: 5bp deducted once for each completed round-trip trade.
- Final factor: `BTC_LONG_5b55989455e686eb_2d`.
- `2d` denotes a maximum holding horizon of about 48 hours; positions for the same factor do not overlap.

## Frozen workflow

1. Factor direction and rolling threshold quantiles are fixed in the development stage.
2. Seven consecutive 180-day selection blocks run from 2022-01-07 inclusive to 2025-06-20 exclusive. The stable tier requires at least five positive blocks; the core tier requires at least six.
3. Candidate de-duplication uses feature-lineage overlap and development-validation score correlation. This freezes a catalogue of 100 factors, including 12 core factors.
4. Scheme 5 requires: core tier, `q=99`, at least six positive selection blocks, and no more than 30% of positive profit contributed by the five largest winning trades.
5. Eligible factors receive equal-weight ordinal ranks on four specified criteria. Rank 1 is frozen as the final factor.
6. The frozen factor is then executed across two consecutive 180-day assessment blocks from 2025-06-20 inclusive to 2026-06-15 exclusive.

## Scheme 5 ranking

The following criteria are ranked independently and summed; the lowest total receives rank 1:

- Cross-stage signal redundancy, ascending;
- Absolute gap between development-validation CAGR and seven-block selection CAGR, ascending;
- Absolute gap between development-validation and seven-block mean gross trade return (bp), ascending;
- Completed trade count in the seven-block selection period, descending.

Ties are resolved by `balanced_cagr` descending, then factor ID ascending.

## Execution sequence

The workflow uses UTC decision timestamps, feature-availability timestamps, and fixed-horizon labels. The final catalogue is recorded before the assessment run; the assessment starts flat and records the catalogue hash at completion. Validation evidence is stored in `evidence/validation.json`.

## Reproduction

Run from this directory:

```bash
./run_full_scheme5.sh
```

The default configuration relies on the verified long-horizon feature table, the original 5bp factor definitions, and the Python environment in the adjacent directory `../btc_factor_fullchain_bundle_cost20bp_20260822/`. It does not regenerate the one-million-candidate search. To protect existing outputs, the command stops if any of these directories already exists:

- `reproduced/selection_7fold/`
- `reproduced/frozen_library/`
- `reproduced/scheme5_final_factor/`
- `reproduced/holdout_2fold/`

For a clean rerun, execute in a new copy of this package.

## Contents

| File or directory | Contents |
|---|---|
| `config.json` | Frozen dates, costs, thresholds, and Scheme 5 rank rules |
| `code/` | Seven-block selection, catalogue freeze, Scheme 5 ranking, assessment, and validation code |
| `reproduced/frozen_library/` | 100-factor frozen catalogue, 12 core factors, de-duplication correlations, and seven-block ledgers |
| `reproduced/scheme5_final_factor/` | Ranking of the four eligible factors and the one-factor final catalogue |
| `reproduced/holdout_2fold/` | Assessment metrics, returns, and completed-trade ledger for the two blocks |
| `evidence/experiment_summary.json` | Experiment summary, artifact locations, and hashes |
| `evidence/validation.json` | Boundary, cost, catalogue, rank, and historical-prefix consistency checks |
| `RESULTS.md` | Reproduced-result summary |

## Research stage

This is a reproducible research package. It does not include evidence on real fills, independent market-impact modelling, live latency, funding costs, or live-trading controls; its current stage is research candidate.
