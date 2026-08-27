from __future__ import annotations

import argparse
import hashlib
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
HOLDOUT_END = pd.Timestamp("2026-06-15", tz="UTC")
COST_BP = 5.0


def load_miner(miner_path: Path, source: Path, cost_bp: float):
    spec = importlib.util.spec_from_file_location("btc_miner_holdout7plus2_test", miner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.SRC = source
    module.COST = cost_bp / 10_000.0
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--miner", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cost-bp", type=float, default=COST_BP)
    args = parser.parse_args()

    source = args.source.resolve()
    run = args.run.resolve()
    catalog_path = args.catalog.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    miner = load_miner(args.miner.resolve(), source, args.cost_bp)
    catalog_hash_before = sha256(catalog_path)
    catalog = pd.read_csv(catalog_path)
    if catalog.factor_id.duplicated().any():
        raise RuntimeError("frozen catalogue contains duplicate factor ids")

    specifications = np.load(run / "candidate_specs.npz")
    schema = pq.read_schema(source)
    base_fields = [
        column
        for column in schema.names
        if column.startswith(("m1_", "x_")) and not column.endswith("available_time")
    ]
    horizons = sorted(catalog.horizon.unique(), key=lambda value: (value[-1], int(value[:-1])))
    columns = ["event_id", "decision_time", "entry_time", "m1_feature_available_time"]
    columns += [f"exit_time_{horizon}" for horizon in horizons]
    columns += [f"return_{horizon}" for horizon in horizons]
    columns += base_fields
    events = pd.read_parquet(
        source,
        columns=columns,
        filters=[("decision_time", "<", HOLDOUT_END.to_pydatetime())],
    )
    time_columns = [
        "decision_time",
        "entry_time",
        "m1_feature_available_time",
        *[f"exit_time_{horizon}" for horizon in horizons],
    ]
    for column in time_columns:
        events[column] = pd.to_datetime(events[column], utc=True)
    if (events.m1_feature_available_time > events.decision_time).any():
        raise RuntimeError("feature availability violation")

    development_positions = np.where((events.decision_time < miner.DEV_END).to_numpy())[0]
    calibration_size = int(len(development_positions) * 0.35)
    calibration = development_positions[:calibration_size]
    features, _, _ = miner.build_atoms(events, base_fields, calibration)
    month_keys = events.decision_time.dt.to_period("M").astype(str)
    month_values = month_keys.unique()
    month_lookup = {value: index for index, value in enumerate(month_values)}
    month_codes = month_keys.map(month_lookup).to_numpy()

    performance_rows: list[dict] = []
    holdout_ledgers: list[pd.DataFrame] = []
    for horizon in horizons:
        holdout_mask = (
            (events.decision_time >= HOLDOUT_START)
            & (events.decision_time < HOLDOUT_END)
            & (events[f"exit_time_{horizon}"] <= HOLDOUT_END)
        ).to_numpy()
        group = catalog[catalog.horizon == horizon].reset_index(drop=True)
        rows = group.candidate_index.to_numpy(int)
        scores = miner.score_specs(features, specifications["idx"], specifications["wid"], rows)
        scores *= group.orientation.to_numpy(np.float32)[None, :]

        thresholds = {
            quantile: np.full((len(month_values), len(group)), np.nan, np.float32)
            for quantile in sorted(group.q.astype(int).unique())
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

        for factor_column, row in group.iterrows():
            quantile = int(row.q)
            event_threshold = thresholds[quantile][month_codes, factor_column]
            # The catalogue is frozen at the boundary; holdout evaluation starts flat
            # and only admits trades whose labels fully mature inside the test window.
            holdout_ledger = miner.nonoverlap(
                events.loc[holdout_mask],
                scores[holdout_mask, factor_column],
                event_threshold[holdout_mask],
                horizon,
            )
            holdout_performance = miner.perf(
                holdout_ledger,
                HOLDOUT_START,
                HOLDOUT_END,
            )
            holdout_ledger["factor_id"] = row.factor_id
            holdout_ledger["scope"] = "historical_holdout_2fold"
            holdout_ledgers.append(holdout_ledger)
            performance_rows.append(
                {
                    "factor_id": row.factor_id,
                    "candidate_index": int(row.candidate_index),
                    "horizon": horizon,
                    "tier_frozen_before_holdout": row.tier,
                    "q_frozen_before_holdout": quantile,
                    "cost_bp": args.cost_bp,
                    "holdout_rank_ic": miner.rcorr(
                        scores[holdout_mask, factor_column],
                        events.loc[holdout_mask, f"return_{horizon}"].to_numpy(float),
                    ),
                    **{
                        f"holdout_{key}": value
                        for key, value in holdout_performance.items()
                    },
                }
            )

    performance = pd.DataFrame(performance_rows)
    ledger = pd.concat(holdout_ledgers, ignore_index=True)
    ledger["holdout_fold"] = (
        (ledger.entry_time - HOLDOUT_START).dt.days // 180
    ).astype(int)
    if len(ledger) and not ledger.holdout_fold.between(0, 1).all():
        raise RuntimeError("holdout trade is outside folds 0..1")
    if len(ledger) and ledger.exit_time.max() > HOLDOUT_END:
        raise RuntimeError("holdout label matured after the test boundary")
    fold_returns = ledger.groupby(["factor_id", "holdout_fold"]).net_return.sum().unstack(
        fill_value=0.0
    )
    fold_returns = fold_returns.reindex(
        index=catalog.factor_id, columns=range(2), fill_value=0.0
    )
    performance = performance.set_index("factor_id")
    performance["positive_holdout_folds"] = (fold_returns > 0).sum(axis=1)
    performance["both_holdout_folds_positive"] = (
        performance.positive_holdout_folds == 2
    )
    performance = performance.reset_index()

    performance.to_csv(
        output / "holdout_2fold_performance.csv", index=False, encoding="utf-8-sig"
    )
    fold_returns.to_csv(output / "holdout_2fold_returns.csv", encoding="utf-8-sig")
    ledger.to_parquet(output / "holdout_trade_ledger.parquet", index=False)
    catalog_hash_after = sha256(catalog_path)
    if catalog_hash_before != catalog_hash_after:
        raise RuntimeError("frozen catalogue changed during holdout evaluation")

    summary = {
        "status": "PASS",
        "meaning": "execution completed; PASS is not an alpha promotion verdict",
        "cost_bp_round_trip": args.cost_bp,
        "holdout_start_inclusive": str(HOLDOUT_START),
        "holdout_end_exclusive": str(HOLDOUT_END),
        "holdout_fold_count": 2,
        "holdout_fold_days": 180,
        "holdout_initial_position": "flat",
        "holdout_boundary_purge": "exit_time_horizon <= 2026-06-15T00:00:00Z",
        "frozen_factor_count": int(len(catalog)),
        "frozen_core_count": int((catalog.tier == "核心").sum()),
        "holdout_factor_count": int(len(performance)),
        "holdout_did_not_select_rank_or_replace_factors": True,
        "catalog_sha256_before": catalog_hash_before,
        "catalog_sha256_after": catalog_hash_after,
        "holdout_positive_aggregate_cagr_count": int((performance.holdout_cagr > 0).sum()),
        "holdout_both_folds_positive_count": int(
            performance.both_holdout_folds_positive.sum()
        ),
        "holdout_trade_rows": int(len(ledger)),
        "script_sha256": sha256(Path(__file__)),
    }
    (output / "holdout_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
