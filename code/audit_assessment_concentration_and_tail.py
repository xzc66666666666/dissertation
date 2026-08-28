#!/usr/bin/env python3
"""Audit assessment-trade concentration and the q=99 tail signal rule.

The script deliberately separates (1) the realised, non-overlapping 5 bp
completed-trade ledger from (2) raw threshold-passing events.  The latter is
the direct diagnostic for the directional information in the q=99 rule and
is therefore computed before overlap selection and transaction costs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


START = pd.Timestamp("2025-06-20T00:00:00Z")
END = pd.Timestamp("2026-06-15T00:00:00Z")
HORIZON = "2d"
FACTOR_SPEC_POSITION = 441884


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float]:
    """Return a two-sided 95% Wilson interval for a binomial hit rate."""
    p = successes / trials
    denominator = 1 + z**2 / trials
    centre = (p + z**2 / (2 * trials)) / denominator
    radius = z * np.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denominator
    return [float(centre - radius), float(centre + radius)]


def load_miner(path: Path):
    spec = importlib.util.spec_from_file_location("assessment_audit_miner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import miner from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.COST = 5.0 / 10_000
    return module


def monthly_concentration(ledger: pd.DataFrame) -> list[dict[str, object]]:
    frame = ledger.copy()
    frame["month"] = frame.exit_time.dt.strftime("%Y-%m")
    records = []
    for month, group in frame.groupby("month", sort=True):
        records.append(
            {
                "month": month,
                "trades": int(len(group)),
                "net_return_sum": float(group.net_return.sum()),
                "positive_return_sum": float(group.loc[group.net_return > 0, "net_return"].sum()),
                "negative_return_sum": float(group.loc[group.net_return < 0, "net_return"].sum()),
            }
        )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-root", required=True, type=Path, help="Full-chain source bundle root")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON (default: evidence/assessment_tail_and_concentration.json)")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    original_root = args.original_root.resolve()
    output = args.output or repo_root / "evidence" / "assessment_tail_and_concentration.json"

    ledger = pd.read_parquet(repo_root / "reproduced/holdout_2fold/holdout_trade_ledger.parquet")
    for column in ("entry_time", "exit_time"):
        ledger[column] = pd.to_datetime(ledger[column], utc=True)
    ledger = ledger.sort_values(["entry_time", "event_id"]).reset_index(drop=True)
    positive = ledger.loc[ledger.net_return > 0].sort_values("net_return", ascending=False)
    gross_positive = float(positive.net_return.sum())

    miner = load_miner(original_root / "code/mine_btc_million_factor_library_v1.py")
    removal = {}
    for label, drop in (("remove_largest_winner", 1), ("remove_top_five_winners", 5)):
        without = ledger.drop(index=positive.index[:drop]).sort_values(["entry_time", "event_id"])
        perf = miner.perf(without, START, END)
        removal[label] = {
            "removed_event_ids": [int(value) for value in positive.event_id.iloc[:drop]],
            "trades_remaining": int(len(without)),
            "compound_total_return": float((1 + without.net_return).prod() - 1),
            "cagr": float(perf["cagr"]),
            "max_drawdown": float(perf["max_drawdown"]),
        }

    source = original_root / "reproduced/full_reproduction_cost20_20260822_01/spot_events_extended_horizons_v1/spot_event_direction_features_extended_horizons.parquet"
    candidate_specs = original_root / "reference_cost5/reproduced/million_long_horizons_cost5_mps/candidate_specs.npz"
    schema = pd.read_parquet(source, engine="pyarrow").columns
    fields = [field for field in schema if field.startswith(("m1_", "x_")) and not field.endswith("available_time")]
    columns = [
        "event_id", "decision_time", "entry_time", "m1_feature_available_time",
        f"exit_time_{HORIZON}", f"return_{HORIZON}", *fields,
    ]
    events = pd.read_parquet(source, columns=columns, filters=[("decision_time", "<", END.to_pydatetime())])
    for column in ("decision_time", "entry_time", "m1_feature_available_time", f"exit_time_{HORIZON}"):
        events[column] = pd.to_datetime(events[column], utc=True)

    dev_positions = np.where((events.decision_time < miner.DEV_END).to_numpy())[0]
    calibration = dev_positions[: int(len(dev_positions) * 0.35)]
    atoms, _, _ = miner.build_atoms(events, fields, calibration)
    specs = np.load(candidate_specs)
    score = miner.score_specs(atoms, specs["idx"], specs["wid"], np.array([FACTOR_SPEC_POSITION], dtype=int))[:, 0] * -1.0
    month_keys = events.decision_time.dt.strftime("%Y-%m")
    monthly_threshold = np.full(len(events), np.nan, dtype=float)
    for month in month_keys.unique():
        selected = month_keys.eq(month).to_numpy()
        first = events.loc[selected, "decision_time"].min()
        history = (events.decision_time < first) & (events.decision_time >= first - pd.Timedelta(days=180))
        if int(history.sum()) >= 500:
            monthly_threshold[selected] = np.nanquantile(np.abs(score[history.to_numpy()]), 0.99)

    tail = events.loc[
        (events.decision_time >= START)
        & (events.decision_time < END)
        & (events[f"exit_time_{HORIZON}"] <= END)
        & np.isfinite(score)
        & np.isfinite(monthly_threshold)
        & (np.abs(score) >= monthly_threshold)
        & events[f"return_{HORIZON}"].notna(),
        ["event_id", "decision_time", f"return_{HORIZON}"],
    ].copy()
    tail["score"] = score[tail.index]
    tail["directional_return"] = np.sign(tail.score) * tail[f"return_{HORIZON}"]
    tail["correct_direction"] = tail.directional_return.gt(0)

    tail_groups = []
    for name, group in tail.groupby(pd.qcut(tail.score.abs(), 4, duplicates="drop"), observed=True):
        hits = int(group.correct_direction.sum())
        tail_groups.append({
            "abs_score_bin": str(name), "events": int(len(group)),
            "mean_directional_gross_return": float(group.directional_return.mean()),
            "hit_rate": float(hits / len(group)), "wilson_95_ci": wilson_interval(hits, len(group)),
        })
    direction_rows = []
    for name, group in tail.assign(direction=np.where(tail.score > 0, "long", "short")).groupby("direction"):
        hits = int(group.correct_direction.sum())
        direction_rows.append({
            "direction": name, "events": int(len(group)),
            "mean_directional_gross_return": float(group.directional_return.mean()),
            "hit_rate": float(hits / len(group)), "wilson_95_ci": wilson_interval(hits, len(group)),
        })
    hits = int(tail.correct_direction.sum())

    report = {
        "scope": {
            "concentration": "49 completed non-overlapping, 5 bp costed trades; exit-date realised-P&L accounting",
            "tail_direction": "87 raw q=99 threshold-passing assessment events; gross 2d directional return, before non-overlap selection and 5 bp costs",
            "status": "Post-selection audit material. It quantifies archived historical results and is not prospective validation or preregistration evidence.",
        },
        "baseline_completed_ledger": {
            "trades": int(len(ledger)),
            "compound_total_return": float((1 + ledger.net_return).prod() - 1),
            "gross_positive_return_sum": gross_positive,
            "largest_winner": {"event_id": int(positive.event_id.iloc[0]), "net_return": float(positive.net_return.iloc[0]), "share_of_gross_positive_returns": float(positive.net_return.iloc[0] / gross_positive)},
            "top_five_winners": {"net_return_sum": float(positive.net_return.iloc[:5].sum()), "share_of_gross_positive_returns": float(positive.net_return.iloc[:5].sum() / gross_positive)},
        },
        "removal_sensitivity": removal,
        "monthly_exit_date_concentration": monthly_concentration(ledger),
        "thresholded_directional_information": {
            "events": int(len(tail)), "directional_hit_rate": float(hits / len(tail)),
            "wilson_95_ci": wilson_interval(hits, len(tail)),
            "mean_directional_gross_return": float(tail.directional_return.mean()),
            "by_direction": direction_rows, "by_abs_score_quartile": tail_groups,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
