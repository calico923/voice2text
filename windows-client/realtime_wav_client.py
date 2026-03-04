#!/usr/bin/env python3
"""Windows validation client for vLLM Realtime API.

This script is intentionally cross-platform so it can be dry-run tested on WSL/Linux.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import inspect
import json
import time
import wave
from pathlib import Path

import websockets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send wav to Realtime API and print events.")
    parser.add_argument("--url", required=True, help="e.g. ws://127.0.0.1:8000/v1/realtime")
    parser.add_argument("--wav", required=True, help="PCM16/16kHz/mono wav path")
    parser.add_argument("--chunk-ms", type=int, default=20, choices=[20, 40])
    parser.add_argument("--receive-timeout", type=float, default=12.0)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--send-response-create", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser


def load_wav(path: Path, chunk_ms: int) -> list[bytes]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm = wf.readframes(wf.getnframes())

    if channels != 1:
        raise ValueError(f"Expected mono wav, got channels={channels}")
    if sample_width != 2:
        raise ValueError(f"Expected PCM16 wav, got sample_width={sample_width}")
    if sample_rate != 16000:
        raise ValueError(f"Expected 16kHz wav, got sample_rate={sample_rate}")

    bytes_per_chunk = int(16000 * chunk_ms / 1000) * 2
    chunks = [pcm[i : i + bytes_per_chunk] for i in range(0, len(pcm), bytes_per_chunk)]
    return [c for c in chunks if c]


async def send_stream(ws, chunks: list[bytes], chunk_ms: int) -> None:
    for i, chunk in enumerate(chunks, 1):
        event = {
            "type": "input_audio_buffer.append",
            "event_id": f"append-{i:05d}",
            "audio": base64.b64encode(chunk).decode("ascii"),
        }
        await ws.send(json.dumps(event, ensure_ascii=False))
        await asyncio.sleep(chunk_ms / 1000.0)

    await ws.send(
        json.dumps(
            {"type": "input_audio_buffer.commit", "event_id": "commit-00001"},
            ensure_ascii=False,
        )
    )


def normalize_result_counters() -> dict[str, int]:
    return {
        "partial": 0,
        "final": 0,
        "error": 0,
        "other": 0,
    }


def classify_event(event_type: str) -> str:
    if event_type == "response.output_text.delta":
        return "partial"
    if event_type == "response.output_text.done":
        return "final"
    if event_type == "error":
        return "error"
    return "other"


async def receive_stream(ws, timeout_sec: float, pretty: bool) -> dict[str, int]:
    counters = normalize_result_counters()
    deadline = time.monotonic() + timeout_sec

    while True:
        remain = deadline - time.monotonic()
        if remain <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remain)
        except asyncio.TimeoutError:
            break
        except websockets.ConnectionClosed:
            break

        try:
            event = json.loads(raw)
            event_type = event.get("type", "")
        except json.JSONDecodeError:
            event = {"raw": raw}
            event_type = ""

        kind = classify_event(event_type)
        counters[kind] += 1

        if pretty:
            print(json.dumps(event, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(event, ensure_ascii=False))

    return counters


async def run(args: argparse.Namespace) -> int:
    wav_path = Path(args.wav)
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV not found: {wav_path}")

    chunks = load_wav(wav_path, args.chunk_ms)
    headers = {}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    print(
        f"[info] url={args.url} wav={wav_path} chunk_ms={args.chunk_ms} chunks={len(chunks)}"
    )
    connect_kwargs = {"max_size": 8_000_000}
    if headers:
        params = inspect.signature(websockets.connect).parameters
        if "additional_headers" in params:
            connect_kwargs["additional_headers"] = headers
        else:
            connect_kwargs["extra_headers"] = headers

    async with websockets.connect(args.url, **connect_kwargs) as ws:
        await send_stream(ws, chunks, args.chunk_ms)
        if args.send_response_create:
            await ws.send(json.dumps({"type": "response.create", "event_id": "response-00001"}))
        counters = await receive_stream(ws, args.receive_timeout, args.pretty)

    print(f"[summary] {json.dumps(counters, ensure_ascii=False)}")
    return 0 if counters["final"] > 0 else 2


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
