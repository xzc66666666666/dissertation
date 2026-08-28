#!/usr/bin/env python3
"""Audit numerical equivalence of the two registered FRPE feature snapshots."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


FEATURES = [
    "x_flow_price_gap",
    "x_close_location",
    "x_flow_mean_12",
    "m1_return_efficiency_5",
    "x_flow_mean_72",
    "x_return_efficiency_288",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_miner(path: Path, cost_bp: float):
    spec = importlib.util.spec_from_file_location("frpe_snapshot_miner", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.COST = cost_bp / 10_000
    return module


def load_events(path: Path, fields: list[str], horizon: str, end: pd.Timestamp) -> pd.DataFrame:
    columns = [
        "event_id",
        "decision_time",
        "entry_time",
        "m1_feature_available_time",
        f"exit_time_{horizon}",
        f"return_{horizon}",
        *fields,
    ]
    frame = pd.read_parquet(
        path,
        columns=columns,
        filters=[("decision_time", "<", end.to_pydatetime())],
    )
    for column in ("decision_time", "entry_time", "m1_feature_available_time", f"exit_time_{horizon}"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def numeric_diff(left: pd.Series, right: pd.Series) -> dict[str, float | int | bool]:
    a = left.to_numpy(float)
    b = right.to_numpy(float)
    finite = np.isfinite(a) & np.isfinite(b)
    delta = np.abs(a[finite] - b[finite])
    return {
        "rows": int(len(a)),
        "left_missing": int((~np.isfinite(a)).sum()),
        "right_missing": int((~np.isfinite(b)).sum()),
        "missing_mask_mismatches": int(np.sum(np.isfinite(a) != np.isfinite(b))),
        "finite_pairs": int(finite.sum()),
        "exact_equal": bool(np.array_equal(a, b, equal_nan=True)),
        "max_abs_diff": float(delta.max()) if len(delta) else 0.0,
        "mean_abs_diff": float(delta.mean()) if len(delta) else 0.0,
        "rmse": float(np.sqrt(np.mean(delta**2))) if len(delta) else 0.0,
        "allclose_rtol_1e-7_atol_1e-9": bool(
            np.allclose(a, b, rtol=1e-7, atol=1e-9, equal_nan=True)
        ),
    }


def thresholds_for_score(events: pd.DataFrame, score: np.ndarray) -> np.ndarray:
    month_keys = events.decision_time.dt.strftime("%Y-%m")
    month_values = month_keys.unique()
    month_lookup = {value: index for index, value in enumerate(month_values)}
    month_codes = month_keys.map(month_lookup).to_numpy()
    monthly = np.full(len(month_values), np.nan, np.float32)
    for month_index in range(len(month_values)):
        first = events.loc[month_codes == month_index, "decision_time"].min()
        history = (events.decision_time < first) & (
            events.decision_time >= first - pd.Timedelta(days=180)
        )
        if history.sum() >= 500:
            monthly[month_index] = np.nanquantile(np.abs(score[history.to_numpy()]), 0.99)
    return monthly[month_codes]


def score_and_threshold(
    miner,
    events: pd.DataFrame,
    fields: list[str],
    candidate_specs: Path,
    candidate_index: int,
    orientation: float,
) -> tuple[np.ndarray, np.ndarray]:
    dev_positions = np.where((events.decision_time < miner.DEV_END).to_numpy())[0]
    calibration = dev_positions[: int(len(dev_positions) * 0.35)]
    atoms, _, _ = miner.build_atoms(events, fields, calibration)
    specs = np.load(candidate_specs)
    score = miner.score_specs(
        atoms,
        specs["idx"],
        specs["wid"],
        np.array([candidate_index], dtype=int),
    )[:, 0]
    score *= orientation
    return score, thresholds_for_score(events, score)


def ledger_summary(
    miner,
    events: pd.DataFrame,
    score: np.ndarray,
    threshold: np.ndarray,
    start: pd.Timestamp,
    end: pd.Timestamp,
    horizon: str,
):
    mask = (
        (events.decision_time >= start)
        & (events.decision_time < end)
        & (events[f"exit_time_{horizon}"] <= end)
    ).to_numpy()
    eligible = (
        mask
        & np.isfinite(score)
        & np.isfinite(threshold)
        & (np.abs(score) >= threshold)
        & events[f"return_{horizon}"].notna().to_numpy()
    )
    ledger = miner.nonoverlap(events.loc[mask], score[mask], threshold[mask], horizon)
    performance = miner.perf(ledger, start, end)
    return eligible, ledger, performance


def records_match(left: pd.DataFrame, right: pd.DataFrame) -> dict[str, object]:
    for frame in (left, right):
        for column in ("entry_time", "exit_time"):
            frame[column] = pd.to_datetime(frame[column], utc=True)
    left = left.sort_values(["entry_time", "event_id"]).reset_index(drop=True)
    right = right.sort_values(["entry_time", "event_id"]).reset_index(drop=True)
    result: dict[str, object] = {
        "left_rows": int(len(left)),
        "right_rows": int(len(right)),
        "event_id_sequence_equal": left.event_id.tolist() == right.event_id.tolist(),
        "event_id_set_equal": set(left.event_id) == set(right.event_id),
    }
    if len(left) == len(right) and result["event_id_sequence_equal"]:
        for column in ("score", "net_return"):
            result[f"{column}_max_abs_diff"] = float(
                np.max(np.abs(left[column].to_numpy(float) - right[column].to_numpy(float)))
            )
        result["entry_time_equal"] = bool((left.entry_time == right.entry_time).all())
        result["exit_time_equal"] = bool((left.exit_time == right.exit_time).all())
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--miner", type=Path, required=True)
    parser.add_argument("--candidate-specs", type=Path, required=True)
    parser.add_argument("--discovery-ledger", type=Path)
    parser.add_argument("--final-ledger", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-index", type=int, default=441884)
    parser.add_argument("--orientation", type=float, default=-1.0)
    parser.add_argument("--cost-bp", type=float, default=5.0)
    parser.add_argument("--horizon", default="2d")
    parser.add_argument("--assessment-start", default="2025-06-20T00:00:00Z")
    parser.add_argument("--assessment-end", default="2026-06-15T00:00:00Z")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = pd.Timestamp(args.assessment_start)
    end = pd.Timestamp(args.assessment_end)
    miner = load_miner(args.miner, args.cost_bp)

    left_schema = pq.read_schema(args.discovery)
    right_schema = pq.read_schema(args.final)
    left_fields = [
        name
        for name in left_schema.names
        if name.startswith(("m1_", "x_")) and not name.endswith("available_time")
    ]
    right_fields = [
        name
        for name in right_schema.names
        if name.startswith(("m1_", "x_")) and not name.endswith("available_time")
    ]
    if left_fields != right_fields:
        raise RuntimeError("base feature schemas differ")

    left = load_events(args.discovery, left_fields, args.horizon, end)
    right = load_events(args.final, right_fields, args.horizon, end)
    key_columns = ["event_id", "decision_time", "entry_time", f"exit_time_{args.horizon}"]
    key_equal = all(left[column].equals(right[column]) for column in key_columns)
    if not key_equal:
        raise RuntimeError("event keys or row order differ")

    assessment = (left.decision_time >= start) & (left.decision_time < end)
    left_score, left_threshold = score_and_threshold(
        miner,
        left,
        left_fields,
        args.candidate_specs,
        args.candidate_index,
        args.orientation,
    )
    right_score, right_threshold = score_and_threshold(
        miner,
        right,
        right_fields,
        args.candidate_specs,
        args.candidate_index,
        args.orientation,
    )
    left_eligible, left_ledger, left_performance = ledger_summary(
        miner, left, left_score, left_threshold, start, end, args.horizon
    )
    right_eligible, right_ledger, right_performance = ledger_summary(
        miner, right, right_score, right_threshold, start, end, args.horizon
    )

    missing_left = left[FEATURES].isna().any(axis=1).to_numpy()
    missing_right = right[FEATURES].isna().any(axis=1).to_numpy()
    complete_case_score = right_score.copy()
    complete_case_score[missing_right] = np.nan
    complete_case_threshold = thresholds_for_score(right, complete_case_score)
    complete_eligible, complete_ledger, complete_performance = ledger_summary(
        miner,
        right,
        complete_case_score,
        complete_case_threshold,
        start,
        end,
        args.horizon,
    )

    report: dict[str, object] = {
        "status": "PASS",
        "inputs": {
            "discovery_file": args.discovery.name,
            "discovery_sha256": sha256(args.discovery),
            "final_file": args.final.name,
            "final_sha256": sha256(args.final),
            "candidate_specs_sha256": sha256(args.candidate_specs),
            "candidate_index": args.candidate_index,
            "orientation": args.orientation,
            "cost_bp": args.cost_bp,
            "assessment_start": start.isoformat(),
            "assessment_end": end.isoformat(),
        },
        "rows": int(len(left)),
        "assessment_rows": int(assessment.sum()),
        "event_keys_and_order_equal": key_equal,
        "feature_schema_equal": left_fields == right_fields,
        "feature_differences_all_rows": {
            name: numeric_diff(left[name], right[name]) for name in FEATURES
        },
        "feature_differences_assessment_rows": {
            name: numeric_diff(left.loc[assessment, name], right.loc[assessment, name])
            for name in FEATURES
        },
        "missing_any_of_six": {
            "discovery_rows": int(missing_left.sum()),
            "final_rows": int(missing_right.sum()),
            "assessment_discovery_rows": int((missing_left & assessment.to_numpy()).sum()),
            "assessment_final_rows": int((missing_right & assessment.to_numpy()).sum()),
            "triggered_discovery_rows_with_missing": int((left_eligible & missing_left).sum()),
            "triggered_final_rows_with_missing": int((right_eligible & missing_right).sum()),
        },
        "score_difference_all_rows": numeric_diff(pd.Series(left_score), pd.Series(right_score)),
        "score_difference_assessment_rows": numeric_diff(
            pd.Series(left_score[assessment.to_numpy()]),
            pd.Series(right_score[assessment.to_numpy()]),
        ),
        "threshold_difference_all_rows": numeric_diff(
            pd.Series(left_threshold), pd.Series(right_threshold)
        ),
        "threshold_difference_assessment_rows": numeric_diff(
            pd.Series(left_threshold[assessment.to_numpy()]),
            pd.Series(right_threshold[assessment.to_numpy()]),
        ),
        "raw_trigger_event_ids": {
            "discovery_count": int(left_eligible.sum()),
            "final_count": int(right_eligible.sum()),
            "set_equal": set(left.loc[left_eligible, "event_id"])
            == set(right.loc[right_eligible, "event_id"]),
            "symmetric_difference_count": int(
                len(
                    set(left.loc[left_eligible, "event_id"])
                    ^ set(right.loc[right_eligible, "event_id"])
                )
            ),
        },
        "nonoverlap_ledger_comparison": records_match(left_ledger.copy(), right_ledger.copy()),
        "performance_discovery": {key: float(value) for key, value in left_performance.items()},
        "performance_final": {key: float(value) for key, value in right_performance.items()},
        "performance_absolute_differences": {
            key: float(abs(left_performance[key] - right_performance[key]))
            for key in left_performance
        },
        "zero_imputation_vs_complete_case": {
            "threshold_difference_assessment_rows": numeric_diff(
                pd.Series(right_threshold[assessment.to_numpy()]),
                pd.Series(complete_case_threshold[assessment.to_numpy()]),
            ),
            "raw_trigger_set_equal": set(right.loc[right_eligible, "event_id"])
            == set(right.loc[complete_eligible, "event_id"]),
            "nonoverlap_ledger_comparison": records_match(
                right_ledger.copy(), complete_ledger.copy()
            ),
            "performance_complete_case": {
                key: float(value) for key, value in complete_performance.items()
            },
            "performance_absolute_differences": {
                key: float(abs(right_performance[key] - complete_performance[key]))
                for key in right_performance
            },
        },
    }
    if args.discovery_ledger:
        report["rerun_discovery_vs_archived_discovery"] = records_match(
            left_ledger.copy(), pd.read_parquet(args.discovery_ledger)
        )
    if args.final_ledger:
        report["rerun_final_vs_archived_final"] = records_match(
            right_ledger.copy(), pd.read_parquet(args.final_ledger)
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
