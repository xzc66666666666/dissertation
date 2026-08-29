#!/usr/bin/env python3
"""Decompose the archived 49-trade assessment ledger by signal direction.

This audit is deliberately downstream-only.  It reads the public completed-
trade ledger and uses the archived accounting identity

    net_return = sign(score) * underlying_2d_return - 0.0005

to report long-only, short-only, and timing-matched always-long variants.
It does not recreate the upstream candidate search or establish executable
fills, prospective validity, or independence from post-selection effects.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ASSESSMENT_DAYS = 360.0
ANNUAL_DAYS = 365.25
COST = 5.0 / 10_000.0


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float]:
    """Return a two-sided 95% Wilson interval for a binomial hit rate."""
    p = successes / trials
    denominator = 1.0 + z**2 / trials
    centre = (p + z**2 / (2.0 * trials)) / denominator
    radius = z * np.sqrt(p * (1.0 - p) / trials + z**2 / (4.0 * trials**2)) / denominator
    return [float(centre - radius), float(centre + radius)]


def performance(returns: pd.Series) -> dict[str, float | int | list[float]]:
    """Compute exit-sequence statistics over the fixed 360-day assessment."""
    values = returns.to_numpy(dtype=float)
    if not len(values):
        raise ValueError("At least one return is required")
    equity = np.cumprod(1.0 + values)
    total_return = float(equity[-1] - 1.0)
    path = np.concatenate(([1.0], equity))
    drawdown = path / np.maximum.accumulate(path) - 1.0
    hits = int(np.sum(values > 0.0))
    return {
        "trades": int(len(values)),
        "winning_trades": hits,
        "net_hit_rate": float(hits / len(values)),
        "net_hit_rate_wilson_95_ci": wilson_interval(hits, len(values)),
        "mean_net_return": float(np.mean(values)),
        "arithmetic_net_return_sum": float(np.sum(values)),
        "compound_total_return": total_return,
        "cagr": float((1.0 + total_return) ** (ANNUAL_DAYS / ASSESSMENT_DAYS) - 1.0),
        "max_drawdown": float(np.min(drawdown)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output or repo_root / "evidence" / "assessment_direction_attribution.json"
    ledger_path = repo_root / "reproduced/holdout_2fold/holdout_trade_ledger.parquet"
    ledger = pd.read_parquet(ledger_path).sort_values(["entry_time", "event_id"]).reset_index(drop=True)

    if len(ledger) != 49:
        raise ValueError(f"Expected 49 completed trades, found {len(ledger)}")
    if ledger["score"].eq(0.0).any():
        raise ValueError("A zero score has no archived trade direction")

    sign = np.where(ledger["score"] > 0.0, 1.0, -1.0)
    ledger["direction"] = np.where(sign > 0.0, "long", "short")
    # Rearrangement of the archived costed-return identity.  This derives the
    # underlying endpoint return without requiring unavailable raw prices.
    ledger["underlying_2d_return"] = sign * (ledger["net_return"] + COST)
    ledger["timing_matched_all_long_net_return"] = ledger["underlying_2d_return"] - COST

    baseline = performance(ledger["net_return"])
    total_arithmetic = float(ledger["net_return"].sum())
    by_direction = {}
    for direction in ("long", "short"):
        subset = ledger.loc[ledger["direction"].eq(direction), "net_return"]
        row = performance(subset)
        row["share_of_baseline_arithmetic_net_return"] = float(subset.sum() / total_arithmetic)
        by_direction[direction] = row

    report = {
        "scope": {
            "ledger": "49 completed non-overlapping assessment trades with the archived 5 bp cost convention",
            "method": "Direction is sign(score). Long-only and short-only retain the corresponding archived trades and remain flat otherwise.",
            "timing_matched_benchmark": "At all 49 archived entry/exit intervals, take a long BTCUSDT position and deduct the same 5 bp cost. The underlying endpoint return is algebraically recovered from the archived costed directional return.",
            "evidential_status": "Downstream retrospective attribution only; not an upstream search reconstruction, independent validation, or executable-fill test.",
        },
        "baseline": baseline,
        "by_archived_direction": by_direction,
        "timing_matched_all_long": performance(ledger["timing_matched_all_long_net_return"]),
        "interpretation": {
            "raw_tail_asymmetry": "The separate 87-trigger audit is long-favouring before non-overlap selection and costs.",
            "completed_ledger": "Both direction subsets contribute positively in the selected 49-trade ledger; long contributes more, but a pure same-timing long benchmark is near flat and has a deeper drawdown.",
            "boundary": "This contrast is descriptive and post-selection. It does not establish stable bidirectional predictability or eliminate regime and selection explanations.",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
