# GitHub Repository Guide

This repository is the code-and-evidence companion for the dissertation's BTCUSDT FRPE-2D post-selection case study. It contains the frozen configuration, selection and assessment code, archived outputs, explicit feature contract, and two new provenance audits.

Public repository: `https://github.com/xzc66666666666/dissertation` on branch `main`.

## Included

- `code/`: selection, ranking, historical assessment, summary, validation, and audit scripts.
- `config.json` and `experiment_manifest.json`: experiment settings and provenance metadata.
- `reproduced/`: archived catalogues, rankings, assessment outputs, and Parquet trade ledgers.
- `evidence/`: workflow checks, feature definitions, source-identity evidence, and snapshot-equivalence results.

## External boundary

The repository does not include the large discovery and final event-feature snapshots, the original one-million-candidate miner, the retained candidate-specification NPZ, the 1,200 upstream definitions, or the cleaned 3,417,120-row minute dataset. These remain in the local research archive and are supplied to the scripts by path.

The absence of those large inputs means a fresh visitor can inspect the code and archived evidence but cannot independently execute the complete raw-data-to-factor chain from this repository alone. The original normalisation program that wrote the cleaned Parquet partitions is also not published. This is a disclosed reproducibility boundary, even though the source identity of all 78 stored partitions has now been independently checked against official Binance USDT-M checksums.

## Full replay

Run in a fresh package copy after providing the external full-chain bundle:

```bash
ORIGINAL_ROOT=/path/to/btc_factor_fullchain_bundle_cost20bp_20260822 \
  ./run_full_scheme5.sh
```

The runner supports `ORIGINAL_ROOT`, `PYTHON`, `MINER`, `SOURCE`, `RUN`, and `ORIGINAL_ROLLING`. It deliberately stops when output directories already exist.

## Audit replay

The two audit scripts require the external snapshots or minute partitions. Their checked outputs are committed in `evidence/`.

```bash
python code/audit_frpe_snapshot_equivalence.py \
  --discovery /path/to/discovery.parquet \
  --final /path/to/final.parquet \
  --miner /path/to/mine_btc_million_factor_library_v1.py \
  --candidate-specs /path/to/candidate_specs.npz \
  --output evidence/frpe_snapshot_equivalence.json

python code/audit_usdtm_source_identity.py \
  --minute-root /path/to/venue_instrument_id=BTCUSDT \
  --spot-gap-csv /path/to/binance_spot_1m_gaps.csv \
  --output evidence/usdtm_source_identity.json
```

## Interpretation

The data contract is Binance BTCUSDT USDT-M perpetual futures. Legacy artifact names containing `spot` are retained only for compatibility. Likewise, `holdout` remains in historical filenames, but the archive does not prove the design was fixed before outcomes were observed. The 2025-2026 period is therefore a historical assessment.

Some frozen CSV/JSON artifacts preserve Chinese categorical values such as the original tier and factor-family labels. The corresponding code keeps those exact values so that catalogue identity and archived hashes remain reproducible; all explanatory documentation and user-facing runner messages are in English.

The experiment remains a research candidate. The fixed 5 bp cost is not a substitute for real fills, bid-ask spread, market impact, funding, liquidation risk, latency, capacity, paper trading, or production controls.
