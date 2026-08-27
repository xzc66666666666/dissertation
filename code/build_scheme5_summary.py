from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    library = root / "reproduced" / "frozen_library"
    final = root / "reproduced" / "scheme5_final_factor"
    holdout = root / "reproduced" / "holdout_2fold"
    final_catalog = pd.read_csv(final / "final_factor_catalog.csv")
    performance = pd.read_csv(holdout / "holdout_2fold_performance.csv")
    if final_catalog.factor_id.tolist() != performance.factor_id.tolist():
        raise RuntimeError("test result does not match scheme 5 final catalogue")
    report = {
        "status": "PASS",
        "meaning": "pipeline reproduction completed; not a deployment verdict",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": "btc_cost5_scheme5_frozen_selection_20260822_v1",
        "cost_bp_round_trip": 5.0,
        "selection": json.loads(
            (library / "selection_summary.json").read_text(encoding="utf-8")
        ),
        "scheme5": json.loads(
            (final / "scheme5_selection_summary.json").read_text(encoding="utf-8")
        ),
        "holdout": json.loads(
            (holdout / "holdout_summary.json").read_text(encoding="utf-8")
        ),
        "selected_factor_id": final_catalog.factor_id.iloc[0],
        "artifacts": {
            "frozen_core_catalog": "reproduced/frozen_library/frozen_factor_catalog.csv",
            "scheme5_ranking": "reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv",
            "final_factor_catalog": "reproduced/scheme5_final_factor/final_factor_catalog.csv",
            "holdout_metrics": "reproduced/holdout_2fold/holdout_2fold_performance.csv",
            "holdout_ledger": "reproduced/holdout_2fold/holdout_trade_ledger.parquet",
        },
        "hashes": {
            "final_factor_catalog": sha256(final / "final_factor_catalog.csv"),
            "scheme5_ranking": sha256(final / "scheme5_candidate_ranking.csv"),
            "holdout_metrics": sha256(holdout / "holdout_2fold_performance.csv"),
            "holdout_ledger": sha256(holdout / "holdout_trade_ledger.parquet"),
        },
    }
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "experiment_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
