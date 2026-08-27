from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def average_absolute_correlation(
    matrix: pd.DataFrame, factor_id: str, comparison_ids: list[str]
) -> float:
    peers = [item for item in comparison_ids if item != factor_id]
    return float(matrix.loc[factor_id, peers].abs().mean())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    library = args.library.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)

    catalog_path = library / "frozen_factor_catalog.csv"
    catalog_hash_before = sha256(catalog_path)
    catalog = pd.read_csv(catalog_path)
    if any(column.startswith("holdout_") for column in catalog.columns):
        raise RuntimeError("frozen selection catalogue contains test metric columns")

    core = catalog[catalog.tier == "核心"].copy()
    eligible = core[
        core.q.eq(99)
        & core.positive_selection_folds.ge(6)
        & core.top_five_selection_profit_share.le(0.30)
    ].copy()
    if eligible.empty:
        raise RuntimeError("scheme 5 has no eligible factor")

    validation_correlation = pd.read_csv(
        library / "development_validation_score_correlation.csv", index_col=0
    )
    selection_correlation = pd.read_csv(
        library / "selection_7fold_score_correlation.csv", index_col=0
    )
    core_ids = core.factor_id.tolist()
    eligible["validation_signal_redundancy"] = [
        average_absolute_correlation(validation_correlation, factor_id, core_ids)
        for factor_id in eligible.factor_id
    ]
    eligible["selection_signal_redundancy"] = [
        average_absolute_correlation(selection_correlation, factor_id, core_ids)
        for factor_id in eligible.factor_id
    ]
    eligible["cross_stage_signal_redundancy"] = eligible[
        ["validation_signal_redundancy", "selection_signal_redundancy"]
    ].max(axis=1)
    eligible["cagr_absolute_gap"] = (
        eligible.validation_cagr - eligible.selection_cagr
    ).abs()
    eligible["mean_gross_bp_absolute_gap"] = (
        eligible.validation_mean_gross_bp - eligible.selection_mean_gross_bp
    ).abs()

    eligible["rank_signal_redundancy"] = eligible.cross_stage_signal_redundancy.rank(
        ascending=True, method="min"
    )
    eligible["rank_cagr_gap"] = eligible.cagr_absolute_gap.rank(
        ascending=True, method="min"
    )
    eligible["rank_mean_gross_bp_gap"] = eligible.mean_gross_bp_absolute_gap.rank(
        ascending=True, method="min"
    )
    eligible["rank_selection_trades"] = eligible.selection_trades.rank(
        ascending=False, method="min"
    )
    eligible["scheme5_rank_sum"] = eligible[
        [
            "rank_signal_redundancy",
            "rank_cagr_gap",
            "rank_mean_gross_bp_gap",
            "rank_selection_trades",
        ]
    ].sum(axis=1)
    eligible = eligible.sort_values(
        ["scheme5_rank_sum", "balanced_cagr", "factor_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    eligible["scheme5_final_rank"] = np.arange(1, len(eligible) + 1)
    eligible["scheme5_selected"] = eligible.scheme5_final_rank.eq(1)
    eligible.to_csv(
        output / "scheme5_candidate_ranking.csv", index=False, encoding="utf-8-sig"
    )

    final_catalog = eligible[eligible.scheme5_selected].copy()
    if len(final_catalog) != 1:
        raise RuntimeError("scheme 5 must freeze exactly one factor")
    final_catalog.to_csv(
        output / "final_factor_catalog.csv", index=False, encoding="utf-8-sig"
    )

    selected_id = final_catalog.factor_id.iloc[0]
    selection_ledger = pd.read_parquet(library / "selection_trade_ledger.parquet")
    validation_ledger = pd.read_parquet(
        library / "development_validation_trade_ledger.parquet"
    )
    selection_ledger[selection_ledger.factor_id.eq(selected_id)].to_parquet(
        output / "final_factor_selection_trade_ledger.parquet", index=False
    )
    validation_ledger[validation_ledger.factor_id.eq(selected_id)].to_parquet(
        output / "final_factor_development_validation_trade_ledger.parquet", index=False
    )

    report = {
        "status": "PASS",
        "experiment_stage": "final pre-test factor freeze",
        "selection_input_end_exclusive": "2025-06-20T00:00:00Z",
        "test_metrics_loaded": False,
        "frozen_core_count": int(len(core)),
        "scheme5_eligible_count": int(len(eligible)),
        "selected_factor_count": 1,
        "selected_factor_id": selected_id,
        "base_gates": {
            "tier": "核心",
            "q": 99,
            "minimum_positive_selection_folds": 6,
            "maximum_top_five_selection_profit_share": 0.30,
        },
        "rank_components": [
            "cross_stage_signal_redundancy ascending",
            "absolute development-to-selection CAGR gap ascending",
            "absolute development-to-selection mean gross bp gap ascending",
            "selection trade count descending",
        ],
        "rank_aggregation": "sum of four ordinal ranks; balanced_cagr descending then factor_id ascending as deterministic tie-breakers",
        "source_catalog_sha256": catalog_hash_before,
        "source_catalog_unchanged": catalog_hash_before == sha256(catalog_path),
        "ranking_sha256": sha256(output / "scheme5_candidate_ranking.csv"),
        "final_catalog_sha256": sha256(output / "final_factor_catalog.csv"),
        "script_sha256": sha256(Path(__file__)),
    }
    (output / "scheme5_selection_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "FROZEN.txt").write_text(
        "Scheme 5 final factor selection reads only artifacts frozen before 2025-06-20 UTC.\n"
        f"selected_factor_id={selected_id}\n"
        f"final_catalog_sha256={report['final_catalog_sha256']}\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
