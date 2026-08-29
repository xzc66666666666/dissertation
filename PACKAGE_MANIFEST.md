# Package Manifest

## Package identity

- Package directory: `btc_factor_scheme5_factor_mining_package_20260823`
- Experiment ID: `btc_cost5_scheme5_frozen_selection_20260822_v1`
- Market: Binance BTCUSDT USDT-M perpetual futures
- Cost: 5 bp per completed round trip
- Final factor: `BTC_LONG_5b55989455e686eb_2d`
- Timing: monthly `q=99` thresholds use the preceding 180 calendar days after at least 500 prior events; archived entry is at least 60 seconds after the decision
- Evidential status: historical assessment; prior external parameter registration is not established

## Code entry points

1. `code/build_selection_7fold.py`: generate the seven selection blocks from 1,200 retained definitions.
2. `code/finalize_selection_7fold.py`: apply tier filters and de-duplication, then archive the 100-factor catalogue for reconstruction.
3. `code/select_scheme5_final_factor.py`: apply Scheme 5 eligibility and rank the candidates.
4. `code/evaluate_holdout_2fold.py`: run the archived reconstruction factor over the historical assessment period. `holdout` is a retained legacy filename, not an evidential claim.
5. `code/build_scheme5_summary.py`: build the archived experiment summary.
6. `code/validate_scheme5_outputs.py`: validate boundaries, catalogue identity, cost convention, and historical-prefix consistency.
7. `code/audit_frpe_snapshot_equivalence.py`: compare the discovery and final snapshots, rebuild scores and thresholds, and compare triggers, ledgers, metrics, and missing-value sensitivity.
8. `code/audit_usdtm_source_identity.py`: compare embedded monthly source hashes with official Binance USDT-M checksums and audit the 2,325 cross-market timestamps.
9. `code/audit_assessment_concentration_and_tail.py`: quantify completed-trade profit concentration and test directional information directly on the raw monthly-q=99 tail triggers.
10. `code/audit_assessment_direction_attribution.py`: decompose the public 49-trade ledger into long-only and short-only variants and construct a timing-matched all-long endpoint benchmark.

## Evidence

| File | Contents |
|---|---|
| `evidence/experiment_summary.json` | Experiment counts, dates, outputs, and hashes |
| `evidence/validation.json` | Archived workflow validation checks |
| `evidence/frpe_feature_contract.json` | Machine-readable definitions of flow and the six FRPE inputs |
| `evidence/frpe_snapshot_equivalence.json` | 49,486-row numerical and economic equivalence audit |
| `evidence/usdtm_source_identity.json` | 78-month official checksum audit and 2,325-timestamp comparison |
| `evidence/assessment_tail_and_concentration.json` | Post-selection audit of 49 completed trades, removal sensitivity, monthly realised-P&L concentration, and 87 raw q=99 triggers |
| `evidence/assessment_direction_attribution.json` | Downstream-only long/short attribution and timing-matched all-long comparison for the 49 archived trade intervals |

## External inputs required for full replay

- The large long-horizon event-feature snapshots;
- The original one-million-candidate miner;
- The original 20,000-stage ledger and complete candidate payoff matrix;
- The retained candidate-specification archive and 1,200 exact definitions;
- Original causal rolling-audit artifacts;
- The cleaned monthly minute partitions for rerunning the source audit;
- Python with NumPy, pandas, and PyArrow.

These large or upstream inputs are not committed to this repository. Some, including the original 20,000-stage ledger and complete candidate payoff matrix, are not available for independent replay. `run_full_scheme5.sh` accepts the retained external inputs through `ORIGINAL_ROOT`, `PYTHON`, `MINER`, `SOURCE`, `RUN`, and `ORIGINAL_ROLLING`. The package therefore supports a partial retrospective reconstruction of the retained search trail, not a full reconstruction of why FRPE-2D won the upstream search.

## Naming note

Historical artifact paths containing `spot` and code paths containing `holdout` are preserved to avoid breaking hashes and replay scripts. The official checksum audit identifies the research data as USDT-M perpetual futures, and the final 360-day period is reported only as a historical assessment.

Immutable categorical values in archived CSV/JSON outputs, including original Chinese tier and factor-family labels, are also preserved because translating them would change catalogue hashes and the replay contract. Repository documentation and user-facing runner messages are English.
