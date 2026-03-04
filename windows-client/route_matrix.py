#!/usr/bin/env python3
"""Run connectivity matrix for localhost / WSL IP / Windows host IP routes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RouteResult:
    route_name: str
    url: str
    return_code: int
    passed: bool
    stdout_tail: str
    stderr_tail: str


def tail_text(text: str, max_chars: int = 1200) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def run_once(route_name: str, url: str, wav: str, chunk_ms: int, timeout: float) -> RouteResult:
    cmd = [
        sys.executable,
        "windows-client/realtime_wav_client.py",
        "--url",
        url,
        "--wav",
        wav,
        "--chunk-ms",
        str(chunk_ms),
        "--receive-timeout",
        str(timeout),
        "--send-response-create",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return RouteResult(
        route_name=route_name,
        url=url,
        return_code=proc.returncode,
        passed=proc.returncode == 0,
        stdout_tail=tail_text(proc.stdout),
        stderr_tail=tail_text(proc.stderr),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Route connectivity matrix runner")
    p.add_argument("--localhost-url", default="ws://127.0.0.1:8000/v1/realtime")
    p.add_argument("--wsl-ip-url", default="ws://172.25.32.1:8000/v1/realtime")
    p.add_argument("--host-ip-url", default="ws://192.168.0.10:8000/v1/realtime")
    p.add_argument("--wav", default="server/testdata/test_ja_1s.wav")
    p.add_argument("--chunk-ms", type=int, default=20, choices=[20, 40])
    p.add_argument("--receive-timeout", type=float, default=12.0)
    p.add_argument(
        "--output",
        default="docs/windows-route-test-result.json",
        help="Path to write matrix result json",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    routes = [
        ("localhost", args.localhost_url),
        ("wsl_ip", args.wsl_ip_url),
        ("windows_host_ip", args.host_ip_url),
    ]

    results = [
        run_once(name, url, args.wav, args.chunk_ms, args.receive_timeout)
        for name, url in routes
    ]
    payload = {
        "wav": args.wav,
        "chunk_ms": args.chunk_ms,
        "receive_timeout": args.receive_timeout,
        "results": [asdict(r) for r in results],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)

    return 0 if any(r.passed for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
