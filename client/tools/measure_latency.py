#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def percentile(sorted_values: list[int], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return float(sorted_values[0])
    if p >= 100:
        return float(sorted_values[-1])

    rank = (len(sorted_values) - 1) * (p / 100.0)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute latency stats from client JSONL")
    p.add_argument("--log", required=True, help="Path to JSONL")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.log)
    if not path.exists():
        raise FileNotFoundError(path)

    latencies: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event_type") == "final_text":
            latency = event.get("latency_ms")
            if isinstance(latency, int) and latency >= 0:
                latencies.append(latency)

    latencies.sort()
    result = {
        "count": len(latencies),
        "min_ms": latencies[0] if latencies else 0,
        "median_ms": round(percentile(latencies, 50), 1),
        "p95_ms": round(percentile(latencies, 95), 1),
        "max_ms": latencies[-1] if latencies else 0,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
