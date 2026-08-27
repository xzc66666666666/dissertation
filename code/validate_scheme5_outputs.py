from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HOLDOUT_START = pd.Timestamp("2025-06-20", tz="UTC")
HOLDOUT_END = pd.Timestamp("2026-06-15", tz="UTC")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--original-rolling", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    selection = root / "reproduced" / "selection_7fold"
    library = root / "reproduced" / "frozen_library"
    final = root / "reproduced" / "scheme5_final_factor"
    holdout = root / "reproduced" / "holdout_2fold"

    frozen_catalog = pd.read_csv(library / "frozen_factor_catalog.csv")
    final_catalog = pd.read_csv(final / "final_factor_catalog.csv")
    ranking = pd.read_csv(final / "scheme5_candidate_ranking.csv")
    performance = pd.read_csv(holdout / "holdout_2fold_performance.csv")
    selection_ledger = pd.read_parquet(library / "selection_trade_ledger.parquet")
    holdout_ledger = pd.read_parquet(holdout / "holdout_trade_ledger.parquet")
    for ledger in (selection_ledger, holdout_ledger):
        ledger.entry_time = pd.to_datetime(ledger.entry_time, utc=True)
        ledger.exit_time = pd.to_datetime(ledger.exit_time, utc=True)

    selection_summary = json.loads(
        (library / "selection_summary.json").read_text(encoding="utf-8")
    )
    scheme5_summary = json.loads(
        (final / "scheme5_selection_summary.json").read_text(encoding="utf-8")
    )
    holdout_summary = json.loads(
        (holdout / "holdout_summary.json").read_text(encoding="utf-8")
    )
    selected_id = final_catalog.factor_id.iloc[0]

    original_rolling = args.original_rolling.resolve()
    original_metrics = pd.read_csv(
        original_rolling / "rolling_strength_cost5_performance.csv"
    ).sort_values("factor_id").reset_index(drop=True)
    selection_metrics = pd.read_csv(
        selection / "selection_strength_cost5_performance.csv"
    ).sort_values("factor_id").reset_index(drop=True)
    original_ledger = pd.read_parquet(
        original_rolling / "historical_pressure_trade_ledgers.parquet"
    )
    original_ledger.entry_time = pd.to_datetime(original_ledger.entry_time, utc=True)
    original_ledger.exit_time = pd.to_datetime(original_ledger.exit_time, utc=True)
    original_ledger = original_ledger[
        (original_ledger.entry_time < HOLDOUT_START)
        & (original_ledger.exit_time <= HOLDOUT_START)
    ].sort_values(["factor_id", "entry_time", "event_id"]).reset_index(drop=True)
    candidate_ledger = pd.read_parquet(
        selection / "stability_selection_trade_ledgers.parquet"
    ).sort_values(["factor_id", "entry_time", "event_id"]).reset_index(drop=True)

    checks = {
        "frozen_core_count_is_12": int((frozen_catalog.tier == "核心").sum()) == 12,
        "scheme5_eligible_count_is_4": len(ranking) == 4,
        "scheme5_selects_exactly_one": len(final_catalog) == 1
        and int(ranking.scheme5_selected.sum()) == 1,
        "selected_factor_is_frozen_core": selected_id
        in set(frozen_catalog.loc[frozen_catalog.tier == "核心", "factor_id"]),
        "selected_factor_is_rank_one": int(
            ranking.loc[ranking.factor_id.eq(selected_id), "scheme5_final_rank"].iloc[0]
        )
        == 1,
        "rank_sum_is_four": float(
            ranking.loc[ranking.factor_id.eq(selected_id), "scheme5_rank_sum"].iloc[0]
        )
        == 4.0,
        "scheme5_loaded_no_test_metrics": not scheme5_summary["test_metrics_loaded"],
        "final_catalog_has_no_test_columns": not any(
            column.startswith("holdout_") for column in final_catalog.columns
        ),
        "test_factor_set_matches_final_catalog": set(performance.factor_id)
        == set(final_catalog.factor_id),
        "test_ledger_factor_set_matches_final_catalog": set(holdout_ledger.factor_id)
        == set(final_catalog.factor_id),
        "selection_trades_end_by_boundary": selection_ledger.empty
        or selection_ledger.exit_time.max() <= HOLDOUT_START,
        "test_trades_start_at_boundary": holdout_ledger.empty
        or holdout_ledger.entry_time.min() >= HOLDOUT_START,
        "test_trades_end_by_boundary": holdout_ledger.empty
        or holdout_ledger.exit_time.max() <= HOLDOUT_END,
        "final_catalog_hash_unchanged_in_test": holdout_summary[
            "catalog_sha256_before"
        ]
        == holdout_summary["catalog_sha256_after"]
        == sha256(final / "final_factor_catalog.csv"),
        "frozen_catalog_hash_matches_selection": selection_summary["catalog_sha256"]
        == sha256(library / "frozen_factor_catalog.csv"),
        "cost_is_5bp": float(selection_summary["cost_bp_round_trip"]) == 5.0
        and float(holdout_summary["cost_bp_round_trip"]) == 5.0,
        "factor_ids_match_original_1200": original_metrics.factor_id.tolist()
        == selection_metrics.factor_id.tolist(),
        "development_q_matches_original": original_metrics.q.equals(selection_metrics.q),
        "development_metrics_match_original": all(
            float((original_metrics[column] - selection_metrics[column]).abs().max())
            == 0.0
            for column in (
                "validation_cagr",
                "validation_sharpe",
                "validation_max_drawdown",
                "validation_rank_ic",
            )
        ),
        "seven_fold_ledger_matches_original_prefix": bool(
            original_ledger[
                ["factor_id", "event_id", "entry_time", "exit_time"]
            ].equals(
                candidate_ledger[
                    ["factor_id", "event_id", "entry_time", "exit_time"]
                ]
            )
            and np.isclose(
                (original_ledger.net_return - candidate_ledger.net_return).abs().max(),
                0.0,
            )
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "status": status,
        "checks": checks,
        "selected_factor_id": selected_id,
        "scheme5_eligible_count": int(len(ranking)),
        "holdout_trade_rows": int(len(holdout_ledger)),
    }
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
