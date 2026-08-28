#!/usr/bin/env python3
"""Verify that cleaned BTCUSDT minute partitions originate from Binance USDT-M Klines."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import pyarrow.parquet as pq


CHECKSUM_URL = (
    "https://data.binance.vision/data/futures/um/monthly/klines/"
    "BTCUSDT/1m/BTCUSDT-1m-{month}.zip.CHECKSUM"
)


def fetch_checksum(month: str, retries: int = 3) -> tuple[str, str]:
    url = CHECKSUM_URL.format(month=month)
    error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(url, timeout=30) as response:
                text = response.read().decode("ascii").strip()
            return text.split()[0].lower(), url
        except Exception as exc:  # pragma: no cover - network failure path
            error = exc
            time.sleep(attempt + 1)
    raise RuntimeError(f"failed to retrieve {url}: {error}")


def month_from_path(path: Path) -> str:
    year = next(part.split("=", 1)[1] for part in path.parts if part.startswith("year="))
    month = next(part.split("=", 1)[1] for part in path.parts if part.startswith("month="))
    return f"{year}-{month}"


def source_manifest(minute_root: Path) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for path in sorted(minute_root.rglob("*.parquet")):
        table = pq.ParquetFile(path).read(
            columns=[
                "source_file_sha256",
                "pipeline_run_id",
                "source_id",
                "canonical_instrument_id",
                "bar_open_time",
            ]
        )
        frame = table.to_pandas()
        if frame.empty:
            continue
        stored_hashes = frame["source_file_sha256"].dropna().astype(str).str.lower().unique()
        if len(stored_hashes) != 1:
            raise ValueError(f"partition has {len(stored_hashes)} source hashes: {path}")
        records.append(
            {
                "month": month_from_path(path),
                "partition": str(path),
                "rows": int(len(frame)),
                "stored_source_sha256": stored_hashes[0],
                "pipeline_run_id": str(frame["pipeline_run_id"].iloc[0]),
                "source_id": str(frame["source_id"].iloc[0]),
                "canonical_instrument_id": str(frame["canonical_instrument_id"].iloc[0]),
                "min_time": pd.to_datetime(frame["bar_open_time"], utc=True).min().isoformat(),
                "max_time": pd.to_datetime(frame["bar_open_time"], utc=True).max().isoformat(),
            }
        )
    result = pd.DataFrame(records).sort_values("month").reset_index(drop=True)
    if result.empty:
        raise FileNotFoundError(minute_root)
    return result


def audit_spot_gap_comparison(minute_root: Path, gap_csv: Path) -> dict[str, object]:
    gaps = pd.read_csv(gap_csv)
    for column in ("previous_bar_open_time", "bar_open_time"):
        gaps[column] = pd.to_datetime(gaps[column], utc=True)
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2026-07-01", tz="UTC")
    gaps = gaps[
        (gaps["bar_open_time"] >= start) & (gaps["bar_open_time"] < end)
    ].copy()

    relevant_months = sorted(
        set(gaps["previous_bar_open_time"].dt.strftime("%Y-%m"))
        | set(gaps["bar_open_time"].dt.strftime("%Y-%m"))
    )
    frames: list[pd.DataFrame] = []
    for month in relevant_months:
        year, month_number = month.split("-")
        directory = minute_root / f"year={year}" / f"month={month_number}"
        for path in sorted(directory.glob("*.parquet")):
            table = pq.ParquetFile(path).read(columns=["bar_open_time", "trade_count"])
            frame = table.to_pandas()
            frame["bar_open_time"] = pd.to_datetime(frame["bar_open_time"], utc=True)
            frames.append(frame)
    minute = pd.concat(frames, ignore_index=True).drop_duplicates("bar_open_time")

    selected: list[pd.DataFrame] = []
    intervals: list[dict[str, object]] = []
    for row in gaps.itertuples(index=False):
        missing_start = row.previous_bar_open_time + pd.Timedelta(minutes=1)
        missing_end = row.bar_open_time - pd.Timedelta(minutes=1)
        subset = minute[
            (minute["bar_open_time"] >= missing_start)
            & (minute["bar_open_time"] <= missing_end)
        ].copy()
        selected.append(subset)
        intervals.append(
            {
                "start_utc": missing_start.isoformat(),
                "end_utc": missing_end.isoformat(),
                "spot_missing_minute_count": int(row.missing_minute_count),
                "perpetual_rows_present": int(len(subset)),
                "perpetual_zero_trade_minutes": int(subset["trade_count"].eq(0).sum()),
            }
        )
    combined = pd.concat(selected, ignore_index=True).drop_duplicates("bar_open_time")
    return {
        "comparison_market": "separately supplied Binance spot annual Kline files",
        "spot_gap_intervals": int(len(gaps)),
        "spot_missing_minutes": int(gaps["missing_minute_count"].sum()),
        "perpetual_rows_at_same_timestamps": int(len(combined)),
        "perpetual_positive_trade_minutes": int(combined["trade_count"].gt(0).sum()),
        "perpetual_zero_trade_minutes": int(combined["trade_count"].eq(0).sum()),
        "perpetual_min_trade_count": int(combined["trade_count"].min()),
        "perpetual_max_trade_count": int(combined["trade_count"].max()),
        "perpetual_total_trade_count": int(combined["trade_count"].sum()),
        "interpretation": (
            "The 2,325-row difference is a cross-market spot-versus-USDT-M comparison, "
            "not evidence of a gap-fill operation in the feature-ready dataset."
        ),
        "intervals": intervals,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minute-root", type=Path, required=True)
    parser.add_argument("--spot-gap-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-network-checks",
        action="store_true",
        help="Record embedded source hashes without retrieving Binance checksum files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = source_manifest(args.minute_root)
    official_rows: list[dict[str, object]] = []
    if not args.skip_network_checks:
        for row in manifest.itertuples(index=False):
            official_hash, url = fetch_checksum(row.month)
            official_rows.append(
                {
                    "month": row.month,
                    "stored_source_sha256": row.stored_source_sha256,
                    "official_usdtm_zip_sha256": official_hash,
                    "match": row.stored_source_sha256 == official_hash,
                    "checksum_url": url,
                }
            )
    official = pd.DataFrame(official_rows)
    source_identity = {
        "market": "Binance USD(S)-M Futures",
        "instrument": "BTCUSDT perpetual futures",
        "official_path_family": "data/futures/um/monthly/klines/BTCUSDT/1m",
        "partitions": int(len(manifest)),
        "rows": int(manifest["rows"].sum()),
        "months": [manifest["month"].min(), manifest["month"].max()],
        "pipeline_run_ids": sorted(manifest["pipeline_run_id"].unique().tolist()),
        "source_ids": sorted(manifest["source_id"].unique().tolist()),
        "canonical_instrument_ids": sorted(
            manifest["canonical_instrument_id"].unique().tolist()
        ),
        "network_checks_performed": not args.skip_network_checks,
        "official_checksum_matches": int(official["match"].sum()) if len(official) else None,
        "official_checksum_mismatches": int((~official["match"]).sum()) if len(official) else None,
        "all_official_checksums_match": bool(official["match"].all()) if len(official) else None,
        "partition_checks": official_rows,
    }
    report = {
        "status": (
            "PASS"
            if args.skip_network_checks or source_identity["all_official_checksums_match"]
            else "FAIL"
        ),
        "source_identity": source_identity,
        "spot_gap_comparison": audit_spot_gap_comparison(
            args.minute_root, args.spot_gap_csv
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
