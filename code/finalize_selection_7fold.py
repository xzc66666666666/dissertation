from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
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


def import_miner(miner_path: Path, source: Path, cost_bp: float):
    specification = importlib.util.spec_from_file_location(
        "btc_miner_holdout7plus2_finalize", miner_path
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    module.SRC = source
    module.COST = cost_bp / 10_000.0
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fields(expression: str) -> list[str]:
    return sorted(set(re.findall(r"(?:m1|x)_[A-Za-z0-9_]+", expression)))


def mechanism_name(expression: str) -> str:
    text = expression.lower()
    if "flow_return_corr" in text or ("flow" in text and "return_efficiency" in text):
        return "主动流与价格响应"
    if "impact_per_flow" in text or "impact_efficiency" in text:
        return "单位主动流冲击"
    if "flow_autocorr" in text or "flow_sign_bias" in text:
        return "主动流持续与反转"
    if "vwap" in text or "close_location" in text:
        return "成交重心与区间位置"
    if "volume_surprise" in text or "trade_surprise" in text:
        return "成交活跃度突变"
    if "realized_vol" in text or "return_vol" in text or "range" in text:
        return "有符号波动与区间扩张"
    if "return_efficiency" in text or "return_sum" in text:
        return "路径效率与漂移"
    return "复合市场状态"


def safe_stat(values: np.ndarray, quantile: float | None = None) -> float | None:
    finite = values[np.isfinite(values)]
    if not len(finite):
        return None
    if quantile is None:
        return float(np.median(finite))
    return float(np.quantile(finite, quantile))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--miner", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--selection-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cost-bp", type=float, default=COST_BP)
    args = parser.parse_args()

    source = args.source.resolve()
    run = args.run.resolve()
    selection_audit = args.selection_audit.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    miner = import_miner(args.miner.resolve(), source, args.cost_bp)

    metrics_path = selection_audit / "selection_strength_cost5_performance.csv"
    metrics = pd.read_csv(metrics_path)
    observed_costs = metrics.cost_bp.dropna().unique()
    if len(observed_costs) != 1 or not np.isclose(observed_costs[0], args.cost_bp):
        raise RuntimeError(
            f"selection cost mismatch: expected {args.cost_bp}bp, observed {observed_costs.tolist()}"
        )
    definitions = pd.read_csv(run / "retained_factor_definitions.csv")
    metrics = metrics.merge(
        definitions,
        on=["factor_id", "candidate_index", "horizon"],
        validate="one_to_one",
    )
    validation_ledger = pd.read_parquet(
        selection_audit / "development_validation_trade_ledgers.parquet"
    )
    selection_ledger = pd.read_parquet(
        selection_audit / "stability_selection_trade_ledgers.parquet"
    )
    for ledger in (validation_ledger, selection_ledger):
        ledger.entry_time = pd.to_datetime(ledger.entry_time, utc=True)
        ledger.exit_time = pd.to_datetime(ledger.exit_time, utc=True)
    if len(selection_ledger) and selection_ledger.entry_time.max() >= HOLDOUT_START:
        raise RuntimeError("holdout trade entered the frozen-library selection")
    if len(selection_ledger) and selection_ledger.exit_time.max() > HOLDOUT_START:
        raise RuntimeError("selection label matured after the holdout boundary")

    selection_ledger["fold"] = (
        (selection_ledger.entry_time - SELECTION_START).dt.days // 180
    ).astype(int)
    if len(selection_ledger) and not selection_ledger.fold.between(0, 6).all():
        raise RuntimeError("selection trade is outside folds 0..6")
    selection_ledger["year"] = selection_ledger.entry_time.dt.year
    fold_returns = selection_ledger.groupby(["factor_id", "fold"]).net_return.sum().unstack(
        fill_value=0.0
    )
    fold_returns = fold_returns.reindex(columns=range(7), fill_value=0.0)
    annual_returns = (
        selection_ledger.groupby(["factor_id", "year"])
        .net_return.apply(lambda values: (1.0 + values).prod() - 1.0)
        .unstack(fill_value=0.0)
    )
    positive = selection_ledger[selection_ledger.net_return > 0].groupby("factor_id").net_return
    top_one_share = positive.apply(lambda values: values.nlargest(1).sum() / values.sum())
    top_five_share = positive.apply(lambda values: values.nlargest(5).sum() / values.sum())

    metrics = metrics.set_index("factor_id")
    metrics["positive_selection_folds"] = (fold_returns > 0).sum(axis=1)
    metrics["worst_selection_fold_return"] = fold_returns.min(axis=1)
    metrics["positive_selection_years"] = (annual_returns > 0).sum(axis=1)
    metrics["top_one_selection_profit_share"] = top_one_share
    metrics["top_five_selection_profit_share"] = top_five_share
    metrics["frequency_retention"] = (
        metrics.selection_trades_per_year / metrics.validation_trades_per_year
    )
    metrics["balanced_cagr"] = np.minimum(metrics.validation_cagr, metrics.selection_cagr)
    metrics["development_candidate"] = (
        (metrics.positive_validation_blocks >= 3)
        & (metrics.validation_cagr >= 0.20)
        & (metrics.validation_sharpe >= 1.0)
        & (metrics.validation_max_drawdown >= -0.35)
        & (metrics.validation_trades_per_year >= 10)
    )
    metrics["historically_stable_candidate"] = (
        (metrics.positive_validation_blocks >= 3)
        & (metrics.validation_cagr >= 0.20)
        & (metrics.validation_sharpe >= 0.8)
        & (metrics.validation_max_drawdown >= -0.40)
        & (metrics.selection_cagr >= 0.10)
        & (metrics.selection_sharpe >= 0.5)
        & (metrics.selection_max_drawdown >= -0.45)
        & (metrics.positive_selection_folds >= 5)
        & (metrics.top_five_selection_profit_share <= 0.40)
    )
    metrics["core_candidate"] = (
        (metrics.positive_validation_blocks >= 3)
        & (metrics.validation_rank_ic > 0)
        & (metrics.validation_cagr >= 0.30)
        & (metrics.validation_sharpe >= 1.2)
        & (metrics.validation_max_drawdown >= -0.25)
        & (metrics.selection_rank_ic > 0)
        & (metrics.selection_cagr >= 0.20)
        & (metrics.selection_sharpe >= 0.8)
        & (metrics.selection_max_drawdown >= -0.30)
        & (metrics.positive_selection_folds >= 6)
        & (metrics.positive_selection_years >= 3)
        & (metrics.top_five_selection_profit_share <= 0.35)
    )

    schema = pq.read_schema(source)
    base_fields = [
        column
        for column in schema.names
        if column.startswith(("m1_", "x_")) and not column.endswith("available_time")
    ]
    event_columns = ["decision_time", "m1_feature_available_time", *base_fields]
    events = pd.read_parquet(
        source,
        columns=event_columns,
        filters=[("decision_time", "<", HOLDOUT_START.to_pydatetime())],
    )
    events.decision_time = pd.to_datetime(events.decision_time, utc=True)
    events.m1_feature_available_time = pd.to_datetime(events.m1_feature_available_time, utc=True)
    if events.decision_time.max() >= HOLDOUT_START:
        raise RuntimeError("holdout row entered final selection")
    if (events.m1_feature_available_time > events.decision_time).any():
        raise RuntimeError("feature availability violation")
    development_positions = np.where((events.decision_time < miner.DEV_END).to_numpy())[0]
    calibration_size = int(len(development_positions) * 0.35)
    calibration = development_positions[:calibration_size]
    validation = development_positions[calibration_size:]
    selection_positions = np.where(
        ((events.decision_time >= SELECTION_START) & (events.decision_time < HOLDOUT_START)).to_numpy()
    )[0]
    feature_matrix, _, _ = miner.build_atoms(events, base_fields, calibration)
    candidate_specs = np.load(run / "candidate_specs.npz")

    stable = metrics[metrics.historically_stable_candidate].sort_values(
        ["balanced_cagr", "selection_sharpe"], ascending=False
    )
    score_cache: dict[str, np.ndarray] = {}
    for _, group in stable.groupby("horizon", sort=False):
        rows = group.candidate_index.to_numpy(int)
        scores = miner.score_specs(
            feature_matrix, candidate_specs["idx"], candidate_specs["wid"], rows
        )
        scores *= group.orientation.to_numpy(np.float32)[None, :]
        for column, factor_id in enumerate(group.index):
            score_cache[factor_id] = scores[:, column]

    selected_ids: list[str] = []
    for factor_id, row in stable.iterrows():
        new_fields = set(fields(str(row.components)))
        duplicate = False
        for old_id in selected_ids:
            old_fields = set(fields(str(metrics.loc[old_id, "components"])))
            overlap = (
                len(new_fields & old_fields) / len(new_fields | old_fields)
                if new_fields | old_fields
                else 1.0
            )
            correlation = np.corrcoef(
                score_cache[factor_id][validation], score_cache[old_id][validation]
            )[0, 1]
            if overlap > 0.50 or (np.isfinite(correlation) and abs(correlation) > 0.55):
                duplicate = True
                break
        if not duplicate:
            selected_ids.append(factor_id)
        if len(selected_ids) >= 100:
            break
    if not selected_ids:
        raise RuntimeError("no factor survived the seven-fold selection")

    selected = metrics.loc[selected_ids].copy()
    selected["tier"] = np.where(selected.core_candidate, "核心", "历史稳定")
    selected["mechanism"] = selected.components.map(mechanism_name)
    selected["input_fields"] = selected.components.map(
        lambda value: "|".join(fields(str(value)))
    )
    selected["latest_availability"] = "m1_feature_available_time <= decision_time"

    score_validation = pd.DataFrame(
        {factor_id: score_cache[factor_id][validation] for factor_id in selected_ids}
    )
    score_selection = pd.DataFrame(
        {factor_id: score_cache[factor_id][selection_positions] for factor_id in selected_ids}
    )
    validation_corr = score_validation.corr()
    selection_corr = score_selection.corr()
    validation_corr.to_csv(output / "development_validation_score_correlation.csv")
    selection_corr.to_csv(output / "selection_7fold_score_correlation.csv")

    selected_selection = selection_ledger[
        selection_ledger.factor_id.isin(selected_ids)
    ].copy()
    selected_selection["day"] = selected_selection.exit_time.dt.floor("D")
    contribution = selected_selection.pivot_table(
        index="day", columns="factor_id", values="net_return", aggfunc="sum", fill_value=0.0
    )
    contribution_corr = contribution.corr()
    contribution_corr.to_csv(output / "selection_7fold_profit_correlation.csv")

    catalog_path = output / "frozen_factor_catalog.csv"
    selected.reset_index().to_csv(catalog_path, index=False, encoding="utf-8-sig")
    metrics.reset_index().to_csv(
        output / "all_exact_candidate_selection_audit.csv", index=False, encoding="utf-8-sig"
    )
    fold_returns.loc[selected_ids].to_csv(
        output / "selection_7fold_180d_returns.csv", encoding="utf-8-sig"
    )
    annual_returns.loc[selected_ids].to_csv(
        output / "selection_annual_returns.csv", encoding="utf-8-sig"
    )
    selected_selection.to_parquet(output / "selection_trade_ledger.parquet", index=False)
    validation_ledger[validation_ledger.factor_id.isin(selected_ids)].to_parquet(
        output / "development_validation_trade_ledger.parquet", index=False
    )

    def off_diagonal(matrix: pd.DataFrame) -> np.ndarray:
        if len(matrix) < 2:
            return np.array([])
        return np.abs(matrix.to_numpy()[np.triu_indices(len(matrix), 1)])

    summary = {
        "status": "PASS",
        "experiment_id": config["experiment_id"],
        "cost_bp_round_trip": args.cost_bp,
        "exact_factor_count": int(len(metrics)),
        "development_candidate_count": int(metrics.development_candidate.sum()),
        "stable_before_dedup": int(metrics.historically_stable_candidate.sum()),
        "core_before_dedup": int(metrics.core_candidate.sum()),
        "selected_after_dedup": int(len(selected)),
        "selected_core_count": int(selected.core_candidate.sum()),
        "selected_by_horizon": selected.groupby("horizon").size().to_dict(),
        "selection_start_inclusive": str(SELECTION_START),
        "selection_end_exclusive": str(HOLDOUT_START),
        "selection_fold_count": 7,
        "selection_boundary_purge": "all selected trades exit no later than holdout start",
        "stable_min_positive_selection_folds": 5,
        "core_min_positive_selection_folds": 6,
        "holdout_rows_loaded_by_selection": False,
        "holdout_metrics_used_for_selection_ranking_or_dedup": False,
        "removed_legacy_full_2025_positive_gate": True,
        "removed_legacy_2026_partial_positive_gate": True,
        "selection_sort": ["min(validation_cagr, selection_cagr)", "selection_sharpe"],
        "dedup_score_window": "development_validation_only",
        "development_validation_score_abs_corr_median": safe_stat(
            off_diagonal(validation_corr)
        ),
        "development_validation_score_abs_corr_p90": safe_stat(
            off_diagonal(validation_corr), 0.90
        ),
        "selection_score_abs_corr_median": safe_stat(off_diagonal(selection_corr)),
        "selection_profit_abs_corr_median": safe_stat(off_diagonal(contribution_corr)),
        "catalog_sha256": sha256(catalog_path),
        "selection_metrics_sha256": sha256(metrics_path),
        "candidate_specs_sha256": sha256(run / "candidate_specs.npz"),
        "config_sha256": sha256(args.config.resolve()),
        "script_sha256": sha256(Path(__file__)),
    }
    (output / "selection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "FROZEN.txt").write_text(
        "This catalogue was selected without loading rows at or after 2025-06-20 UTC.\n"
        f"catalog_sha256={summary['catalog_sha256']}\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
