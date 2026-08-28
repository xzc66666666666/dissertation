# GitHub repository guide

This repository is the code-and-evidence companion for the dissertation's BTCUSDT
FRPE-2D post-selection assessment. It contains the six Python entry points, the
frozen configuration, validation evidence, and the reproduced selection and
holdout ledgers used by the thesis.

Public repository: https://github.com/xzc66666666666/dissertation.git (main,
commit `d53a32f7ad199a3846ab50e7f4dbf0021e05a9b6`).

## What is included

- `code/`: selection, ranking, holdout evaluation, summary, and validation scripts.
- `config.json` and `experiment_manifest.json`: frozen experiment settings and
  provenance metadata.
- `reproduced/`: archived outputs used in the dissertation, including Parquet
  trade ledgers.
- `evidence/`: validation results and experiment summary.

## Reproduction boundary

The repository does **not** contain the upstream long-horizon feature snapshot,
the original one-million-candidate miner, or the original 1,200 retained factor
definitions. Those inputs remain in the local research archive referenced by
`run_full_scheme5.sh`. The script accepts these locations through `ORIGINAL_ROOT`,
`PYTHON`, `MINER`, `SOURCE`, `RUN`, and `ORIGINAL_ROLLING` environment variables.
It deliberately stops when output directories already exist, so run it from a
fresh copy when performing a full replay.

Example:

```bash
ORIGINAL_ROOT=/path/to/btc_factor_fullchain_bundle_cost20bp_20260822 \\
  ./run_full_scheme5.sh
```

Install an environment containing NumPy, pandas, and PyArrow before running the
scripts. The archived outputs are the authoritative evidence for the dissertation
version; a fresh replay should be compared with them using
`code/validate_scheme5_outputs.py`.

## Interpretation and safety

The experiment is a research candidate. The fixed 5 bp cost is not a substitute
for real fills, bid-ask spread, market impact, financing, latency, capacity, or
paper-trading evidence. Do not use this repository as an automated live-trading
system without a separate execution adapter and risk controls.
