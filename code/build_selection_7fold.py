from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


SELECTION_START = pd.Timestamp("2022-01-07", tz="UTC")
HOLDOUT_START = pd.Timestamp("2025-06-20", tz="UTC")
COST_BP = 5.0


def load_miner(miner_path: Path, source: Path, cost_bp: float):
    spec = importlib.util.spec_from_file_location("btc_miner_holdout7plus2_selection", miner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.SRC = source
    module.COST = cost_bp / 10_000.0
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--miner", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cost-bp", type=float, default=COST_BP)
    args = parser.parse_args()

    source = args.source.resolve()
    run = args.run.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    miner = load_miner(args.miner.resolve(), source, args.cost_bp)

    definitions = pd.read_csv(run / "retained_factor_definitions.csv")
    specifications = np.load(run / "candidate_specs.npz")
    candidate_indices = specifications["idx"]
    candidate_weights = specifications["wid"]

    schema = pq.read_schema(source)
    base_fields = [
        column
        for column in schema.names
        if column.startswith(("m1_", "x_")) and not column.endswith("available_time")
    ]
    horizons = sorted(definitions.horizon.unique(), key=lambda value: (value[-1], int(value[:-1])))
    columns = ["event_id", "decision_time", "entry_time", "m1_feature_available_time"]
    columns += [f"exit_time_{horizon}" for horizon in horizons]
    columns += [f"return_{horizon}" for horizon in horizons]
    columns += base_fields

    # Selection process cannot load rows from the holdout interval.
    events = pd.read_parquet(
        source,
        columns=columns,
        filters=[("decision_time", "<", HOLDOUT_START.to_pydatetime())],
    )
    time_columns = [
        "decision_time",
        "entry_time",
        "m1_feature_available_time",
        *[f"exit_time_{horizon}" for horizon in horizons],
    ]
    for column in time_columns:
        events[column] = pd.to_datetime(events[column], utc=True)
    if events.decision_time.max() >= HOLDOUT_START:
        raise RuntimeError("holdout row entered the selection process")
    if (events.m1_feature_available_time > events.decision_time).any():
        raise RuntimeError("feature availability violation")

    development_positions = np.where((events.decision_time < miner.DEV_END).to_numpy())[0]
    calibration_size = int(len(development_positions) * 0.35)
    calibration = development_positions[:calibration_size]
    validation = development_positions[calibration_size:]
    validation_blocks = np.array_split(validation, 4)
    cross_boundary_labels_masked: dict[str, int] = {}
    for horizon in horizons:
        crosses_boundary = events[f"exit_time_{horizon}"] > HOLDOUT_START
        cross_boundary_labels_masked[horizon] = int(crosses_boundary.sum())
        events.loc[crosses_boundary, f"return_{horizon}"] = np.nan
    features, _, _ = miner.build_atoms(events, base_fields, calibration)

    month_keys = events.decision_time.dt.to_period("M").astype(str)
    month_values = month_keys.unique()
    month_lookup = {value: index for index, value in enumerate(month_values)}
    month_codes = month_keys.map(month_lookup).to_numpy()

    results: list[dict] = []
    validation_ledgers: list[pd.DataFrame] = []
    selection_ledgers: list[pd.DataFrame] = []
    for horizon in horizons:
        selection_mask = (
            (events.decision_time >= SELECTION_START)
            & (events.decision_time < HOLDOUT_START)
            & (events[f"exit_time_{horizon}"] <= HOLDOUT_START)
        ).to_numpy()
        horizon_definitions = definitions[definitions.horizon == horizon].reset_index(drop=True)
        rows = horizon_definitions.candidate_index.to_numpy(int)
        scores = miner.score_specs(features, candidate_indices, candidate_weights, rows)
        scores *= horizon_definitions.orientation.to_numpy(np.float32)[None, :]

        thresholds = {
            quantile: np.full((len(month_values), len(rows)), np.nan, np.float32)
            for quantile in (95, 97, 99)
        }
        for month_index in range(len(month_values)):
            first = events.loc[month_codes == month_index, "decision_time"].min()
            history = (events.decision_time < first) & (
                events.decision_time >= first - pd.Timedelta(days=180)
            )
            if history.sum() < 500:
                continue
            absolute_scores = np.abs(scores[history.to_numpy()])
            for quantile in thresholds:
                thresholds[quantile][month_index] = np.nanquantile(
                    absolute_scores, quantile / 100.0, axis=0
                )

        for factor_column, row in horizon_definitions.iterrows():
            alternatives = []
            for quantile in thresholds:
                event_threshold = thresholds[quantile][month_codes, factor_column]
                block_means = []
                for block in validation_blocks:
                    block_ledger = miner.nonoverlap(
                        events.loc[block],
                        scores[block, factor_column],
                        event_threshold[block],
                        horizon,
                    )
                    block_means.append(
                        block_ledger.net_return.mean() * 10_000 if len(block_ledger) else np.nan
                    )
                validation_ledger = miner.nonoverlap(
                    events.loc[validation],
                    scores[validation, factor_column],
                    event_threshold[validation],
                    horizon,
                )
                validation_performance = miner.perf(
                    validation_ledger,
                    events.loc[validation, "decision_time"].min(),
                    events.loc[validation, "decision_time"].max(),
                )
                valid = (
                    np.sum(np.asarray(block_means) > 0) >= 3
                    and validation_performance["trades_per_year"] >= 10
                    and validation_performance["cagr"] > 0
                )
                key = (
                    valid,
                    validation_performance["calmar"]
                    if np.isfinite(validation_performance["calmar"])
                    else -999,
                    validation_performance["cagr"],
                )
                alternatives.append(
                    (
                        key,
                        quantile,
                        event_threshold,
                        block_means,
                        validation_performance,
                        validation_ledger,
                    )
                )

            _, quantile, event_threshold, block_means, validation_performance, validation_ledger = max(
                alternatives, key=lambda item: item[0]
            )
            validation_ledger["factor_id"] = row.factor_id
            validation_ledger["scope"] = "development_validation"
            validation_ledgers.append(validation_ledger)

            selection_ledger = miner.nonoverlap(
                events.loc[selection_mask],
                scores[selection_mask, factor_column],
                event_threshold[selection_mask],
                horizon,
            )
            selection_performance = miner.perf(
                selection_ledger,
                SELECTION_START,
                HOLDOUT_START,
            )
            selection_ledger["factor_id"] = row.factor_id
            selection_ledger["scope"] = "stability_selection_7fold"
            selection_ledgers.append(selection_ledger)
            results.append(
                {
                    "factor_id": row.factor_id,
                    "candidate_index": int(row.candidate_index),
                    "horizon": horizon,
                    "cost_bp": args.cost_bp,
                    "q": int(quantile),
                    "positive_validation_blocks": int(np.sum(np.asarray(block_means) > 0)),
                    "worst_validation_block_bp": float(np.nanmin(block_means)),
                    "validation_rank_ic": miner.rcorr(
                        scores[validation, factor_column],
                        events.loc[validation, f"return_{horizon}"].to_numpy(float),
                    ),
                    **{
                        f"validation_{key}": value
                        for key, value in validation_performance.items()
                    },
                    "selection_rank_ic": miner.rcorr(
                        scores[selection_mask, factor_column],
                        events.loc[selection_mask, f"return_{horizon}"].to_numpy(float),
                    ),
                    **{
                        f"selection_{key}": value
                        for key, value in selection_performance.items()
                    },
                }
            )

    result_frame = pd.DataFrame(results)
    result_frame["frequency_retention"] = (
        result_frame.selection_trades_per_year / result_frame.validation_trades_per_year
    )
    result_frame["balanced_cagr"] = np.minimum(
        result_frame.validation_cagr, result_frame.selection_cagr
    )
    result_frame.to_csv(
        output / "selection_strength_cost5_performance.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.concat(validation_ledgers, ignore_index=True).to_parquet(
        output / "development_validation_trade_ledgers.parquet", index=False
    )
    pd.concat(selection_ledgers, ignore_index=True).to_parquet(
        output / "stability_selection_trade_ledgers.parquet", index=False
    )
    audit = {
        "status": "PASS",
        "cost_bp_round_trip": args.cost_bp,
        "threshold_rule": "monthly causal percentile from prior 180 calendar days",
        "threshold_candidates_selected_in_development_validation": [95, 97, 99],
        "formula_orientation_and_q_use_holdout": False,
        "selection_process_loaded_holdout_rows": False,
        "selection_start_inclusive": str(SELECTION_START),
        "selection_end_exclusive": str(HOLDOUT_START),
        "selection_fold_count": 7,
        "selection_fold_days": 180,
        "selection_boundary_purge": "exit_time_horizon <= 2025-06-20T00:00:00Z",
        "cross_boundary_labels_masked": cross_boundary_labels_masked,
        "factor_count": int(len(result_frame)),
        "maximum_decision_time_loaded": str(events.decision_time.max()),
    }
    (output / "run_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
