#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUMMARY_RE = re.compile(
    r"summary:\s*finals=(?P<finals>\d+)\s+partial_present=(?P<partial>True|False)\s+error=(?P<error>.*)"
)


@dataclass
class RunRecord:
    run_index: int
    started_at: str
    ended_at: str
    elapsed_ms: int
    return_code: int
    finals: int
    partial_present: bool
    error: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def parse_main_summary(stdout_text: str) -> tuple[int, bool, str]:
    last: tuple[int, bool, str] | None = None
    for line in stdout_text.splitlines():
        m = SUMMARY_RE.search(line.strip())
        if not m:
            continue
        finals = int(m.group("finals"))
        partial_present = m.group("partial") == "True"
        error = m.group("error").strip()
        last = (finals, partial_present, error)
    if last is None:
        return (0, False, "summary_not_found")
    return last


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def collect_event_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "send_commit_count": 0,
            "final_text_count": 0,
            "error_event_count": 0,
            "latencies_ms": [],
        }

    send_commit_count = 0
    final_text_count = 0
    error_event_count = 0
    latencies_ms: list[int] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("event_type")
        if event_type == "send_commit":
            send_commit_count += 1
        elif event_type == "final_text":
            final_text_count += 1
            latency = event.get("latency_ms")
            if isinstance(latency, int) and latency >= 0:
                latencies_ms.append(latency)
        elif event_type == "error":
            error_event_count += 1

    return {
        "send_commit_count": send_commit_count,
        "final_text_count": final_text_count,
        "error_event_count": error_event_count,
        "latencies_ms": latencies_ms,
    }


def summarize_vram_samples(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "reason": "vram_log_not_found", "sample_count": 0}

    samples: list[dict[str, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        used = payload.get("memory_used_mb")
        free = payload.get("memory_free_mb")
        total = payload.get("memory_total_mb")
        if all(isinstance(v, int) for v in (used, free, total)):
            samples.append(
                {
                    "used": int(used),
                    "free": int(free),
                    "total": int(total),
                }
            )

    if not samples:
        return {"available": False, "reason": "no_numeric_samples", "sample_count": 0}

    used_values = [s["used"] for s in samples]
    free_values = [s["free"] for s in samples]
    total_values = [s["total"] for s in samples]
    return {
        "available": True,
        "sample_count": len(samples),
        "memory_used_mb": {
            "min": min(used_values),
            "max": max(used_values),
            "avg": round(sum(used_values) / len(used_values), 1),
        },
        "memory_free_mb": {
            "min": min(free_values),
            "max": max(free_values),
            "avg": round(sum(free_values) / len(free_values), 1),
        },
        "memory_total_mb": {
            "min": min(total_values),
            "max": max(total_values),
            "avg": round(sum(total_values) / len(total_values), 1),
        },
    }


class VramSampler:
    def __init__(self, path: Path, interval_sec: float) -> None:
        self.path = path
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._nvidia_smi = shutil.which("nvidia-smi")

    @property
    def enabled(self) -> bool:
        return self._nvidia_smi is not None

    def start(self) -> None:
        if not self.enabled:
            append_jsonl(
                self.path,
                {
                    "captured_at": utc_now_iso(),
                    "event": "vram_sampling_unavailable",
                    "reason": "nvidia-smi not found",
                },
            )
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        assert self._nvidia_smi is not None
        cmd = [
            self._nvidia_smi,
            "--query-gpu=timestamp,memory.used,memory.free,memory.total",
            "--format=csv,noheader,nounits",
        ]
        while not self._stop.is_set():
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
                raw = proc.stdout.splitlines()[0].strip() if proc.returncode == 0 and proc.stdout else ""
                parts = [p.strip() for p in raw.split(",")] if raw else []
                if len(parts) >= 4:
                    append_jsonl(
                        self.path,
                        {
                            "captured_at": utc_now_iso(),
                            "gpu_timestamp": parts[0],
                            "memory_used_mb": int(parts[1]),
                            "memory_free_mb": int(parts[2]),
                            "memory_total_mb": int(parts[3]),
                        },
                    )
                else:
                    append_jsonl(
                        self.path,
                        {
                            "captured_at": utc_now_iso(),
                            "event": "vram_parse_error",
                            "raw": raw,
                            "stderr": proc.stderr.strip(),
                        },
                    )
            except (subprocess.SubprocessError, ValueError) as exc:
                append_jsonl(
                    self.path,
                    {
                        "captured_at": utc_now_iso(),
                        "event": "vram_sampling_error",
                        "error": str(exc),
                    },
                )
            self._stop.wait(self.interval_sec)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Continuous operation evaluator (T17)")
    p.add_argument("--wav", required=True)
    p.add_argument("--url", default="ws://127.0.0.1:8000/v1/realtime")
    p.add_argument("--duration-minutes", type=float, default=30.0)
    p.add_argument("--chunk-ms", type=int, default=20, choices=[20, 40])
    p.add_argument("--receive-timeout", type=float, default=12.0)
    p.add_argument("--cooldown-sec", type=float, default=0.2)
    p.add_argument("--vram-interval-sec", type=float, default=5.0)
    p.add_argument("--output-dir", default="client/logs/continuous")
    p.add_argument("--max-runs", type=int, default=0, help="0 means unlimited within duration")
    p.add_argument("--python-exe", default=sys.executable)
    p.add_argument("--no-response-create", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    main_py = repo_root / "client" / "src" / "main.py"
    wav_path = (repo_root / args.wav).resolve() if not Path(args.wav).is_absolute() else Path(args.wav)
    if not wav_path.exists():
        raise FileNotFoundError(f"wav not found: {wav_path}")
    if args.duration_minutes <= 0:
        raise ValueError("--duration-minutes must be > 0")

    started_at = utc_now_iso()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (repo_root / args.output_dir / run_id).resolve()
    runs_dir = run_dir / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    events_log = run_dir / "events.jsonl"
    runs_log = run_dir / "run_records.jsonl"
    vram_log = run_dir / "vram.jsonl"
    summary_path = run_dir / "summary.json"

    sampler = VramSampler(vram_log, args.vram_interval_sec)
    sampler.start()

    deadline = time.monotonic() + (args.duration_minutes * 60)
    max_runs = args.max_runs if args.max_runs > 0 else None
    run_count = 0
    run_success = 0

    try:
        while time.monotonic() < deadline:
            if max_runs is not None and run_count >= max_runs:
                break

            run_count += 1
            one_started = utc_now_iso()
            t0 = time.monotonic()

            env = os.environ.copy()
            env["LOG_TO_FILE"] = "true"
            env["LOG_FILE"] = str(events_log)
            env["AUTO_PASTE"] = "false"

            cmd = [
                args.python_exe,
                str(main_py),
                "--wav",
                str(wav_path),
                "--url",
                args.url,
                "--chunk-ms",
                str(args.chunk_ms),
                "--receive-timeout",
                str(args.receive_timeout),
            ]
            if args.no_response_create:
                cmd.append("--no-response-create")

            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root), env=env)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            one_ended = utc_now_iso()
            finals, partial_present, error = parse_main_summary(proc.stdout)
            record = RunRecord(
                run_index=run_count,
                started_at=one_started,
                ended_at=one_ended,
                elapsed_ms=elapsed_ms,
                return_code=proc.returncode,
                finals=finals,
                partial_present=partial_present,
                error=error,
            )
            append_jsonl(runs_log, asdict(record))

            (runs_dir / f"{run_count:04d}.stdout.log").write_text(proc.stdout, encoding="utf-8")
            (runs_dir / f"{run_count:04d}.stderr.log").write_text(proc.stderr, encoding="utf-8")

            if proc.returncode == 0 and finals > 0:
                run_success += 1

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if args.cooldown_sec > 0:
                time.sleep(min(args.cooldown_sec, max(0.0, remaining)))
    finally:
        sampler.stop()

    finished_at = utc_now_iso()
    event_metrics = collect_event_metrics(events_log)
    latencies = sorted(event_metrics["latencies_ms"])
    missing_final_count = max(0, event_metrics["send_commit_count"] - event_metrics["final_text_count"])
    missing_final_rate_pct = (
        round((missing_final_count / event_metrics["send_commit_count"]) * 100.0, 2)
        if event_metrics["send_commit_count"] > 0
        else 0.0
    )

    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_requested_minutes": args.duration_minutes,
        "duration_actual_seconds": round(
            (
                datetime.fromisoformat(finished_at).timestamp()
                - datetime.fromisoformat(started_at).timestamp()
            ),
            1,
        ),
        "config": {
            "url": args.url,
            "wav": str(wav_path),
            "chunk_ms": args.chunk_ms,
            "receive_timeout": args.receive_timeout,
            "cooldown_sec": args.cooldown_sec,
            "vram_interval_sec": args.vram_interval_sec,
            "max_runs": args.max_runs,
            "protocol": "session.update + input_audio_buffer.commit(final=true)",
            "response_create_supported": False,
            "deprecated_no_response_create_flag": args.no_response_create,
        },
        "run_metrics": {
            "attempted_runs": run_count,
            "successful_runs": run_success,
            "success_rate_pct": round((run_success / run_count) * 100.0, 2) if run_count > 0 else 0.0,
        },
        "event_metrics": {
            "send_commit_count": event_metrics["send_commit_count"],
            "final_text_count": event_metrics["final_text_count"],
            "error_event_count": event_metrics["error_event_count"],
            "missing_final_count": missing_final_count,
            "missing_final_rate_pct": missing_final_rate_pct,
        },
        "latency_metrics_ms": {
            "count": len(latencies),
            "min": latencies[0] if latencies else 0,
            "median": round(percentile(latencies, 50), 1),
            "p95": round(percentile(latencies, 95), 1),
            "max": latencies[-1] if latencies else 0,
        },
        "vram_metrics": summarize_vram_samples(vram_log),
        "artifacts": {
            "events_jsonl": str(events_log),
            "run_records_jsonl": str(runs_log),
            "vram_jsonl": str(vram_log),
            "runs_dir": str(runs_dir),
        },
    }

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary_path)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if run_success > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
