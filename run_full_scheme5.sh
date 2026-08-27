#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ORIGINAL_ROOT=${ORIGINAL_ROOT:-"$ROOT/../btc_factor_fullchain_bundle_cost20bp_20260822"}
PYTHON=${PYTHON:-"$ORIGINAL_ROOT/.venv-factors-mac/bin/python"}
MINER=${MINER:-"$ORIGINAL_ROOT/code/mine_btc_million_factor_library_v1.py"}
SOURCE=${SOURCE:-"$ORIGINAL_ROOT/reproduced/full_reproduction_cost20_20260822_01/spot_events_extended_horizons_v1/spot_event_direction_features_extended_horizons.parquet"}
RUN=${RUN:-"$ORIGINAL_ROOT/reference_cost5/reproduced/million_long_horizons_cost5_mps"}
ORIGINAL_ROLLING=${ORIGINAL_ROLLING:-"$RUN/causal_rolling_strength_audit_v1"}
SELECTION="$ROOT/reproduced/selection_7fold"
LIBRARY="$ROOT/reproduced/frozen_library"
FINAL="$ROOT/reproduced/scheme5_final_factor"
HOLDOUT="$ROOT/reproduced/holdout_2fold"

test -x "$PYTHON" || { echo "Python运行环境不存在: $PYTHON" >&2; exit 2; }
test -f "$MINER" || { echo "矿工脚本不存在: $MINER" >&2; exit 2; }
test -f "$SOURCE" || { echo "长周期特征表不存在: $SOURCE" >&2; exit 2; }
test -f "$RUN/retained_factor_definitions.csv" || { echo "5bp的1,200条冻结定义不存在: $RUN" >&2; exit 2; }
test ! -e "$SELECTION" || { echo "输出已存在: $SELECTION" >&2; exit 2; }
test ! -e "$LIBRARY" || { echo "输出已存在: $LIBRARY" >&2; exit 2; }
test ! -e "$FINAL" || { echo "输出已存在: $FINAL" >&2; exit 2; }
test ! -e "$HOLDOUT" || { echo "输出已存在: $HOLDOUT" >&2; exit 2; }

mkdir -p "$ROOT/reproduced"

"$PYTHON" "$ROOT/code/build_selection_7fold.py" \
  --miner "$MINER" --source "$SOURCE" --run "$RUN" \
  --output "$SELECTION" --cost-bp 5

"$PYTHON" "$ROOT/code/finalize_selection_7fold.py" \
  --miner "$MINER" --source "$SOURCE" --run "$RUN" \
  --selection-audit "$SELECTION" --output "$LIBRARY" \
  --config "$ROOT/config.json" --cost-bp 5

"$PYTHON" "$ROOT/code/select_scheme5_final_factor.py" \
  --library "$LIBRARY" --output "$FINAL"

"$PYTHON" "$ROOT/code/evaluate_holdout_2fold.py" \
  --miner "$MINER" --source "$SOURCE" --run "$RUN" \
  --catalog "$FINAL/final_factor_catalog.csv" \
  --output "$HOLDOUT" --cost-bp 5

"$PYTHON" "$ROOT/code/build_scheme5_summary.py" --root "$ROOT"
"$PYTHON" "$ROOT/code/validate_scheme5_outputs.py" --root "$ROOT" \
  --original-rolling "$ORIGINAL_ROLLING"

echo "完成：$ROOT/evidence/experiment_summary.json"
