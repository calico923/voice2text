#!/usr/bin/env python3
"""Local smoke client for vLLM Realtime API."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
import wave
from pathlib import Path

import websockets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Realtime local smoke client")
    parser.add_argument("--url", default="ws://127.0.0.1:8000/v1/realtime")
    parser.add_argument("--wav", required=True, help="PCM16/16kHz/mono wav path")
    parser.add_argument("--chunk-ms", type=int, default=20, choices=[20, 40])
    parser.add_argument("--api-key", default="", help="Optional bearer token")
    parser.add_argument("--receive-timeout", type=float, default=8.0)
    parser.add_argument(
        "--skip-response-create",
        action="store_true",
        help="Do not send response.create event",
    )
    return parser.parse_args()


def load_wav_frames(path: Path, chunk_ms: int) -> list[bytes]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm = wf.readframes(wf.getnframes())

    if channels != 1:
        raise ValueError(f"wav must be mono, got channels={channels}")
    if sample_width != 2:
        raise ValueError(f"wav must be PCM16, got sample_width={sample_width}")
    if sample_rate != 16000:
        raise ValueError(f"wav must be 16kHz, got sample_rate={sample_rate}")

    bytes_per_frame = int((16000 * chunk_ms / 1000) * 2)
    if bytes_per_frame <= 0:
        raise ValueError("invalid bytes_per_frame")

    frames = [pcm[i : i + bytes_per_frame] for i in range(0, len(pcm), bytes_per_frame)]
    return [f for f in frames if f]


async def send_audio(ws, frames: list[bytes], chunk_ms: int) -> None:
    for i, frame in enumerate(frames, 1):
        payload = {
            "type": "input_audio_buffer.append",
            "event_id": f"append-{i:04d}",
            "audio": base64.b64encode(frame).decode("ascii"),
        }
        await ws.send(json.dumps(payload, ensure_ascii=False))
        await asyncio.sleep(chunk_ms / 1000.0)

    await ws.send(
        json.dumps(
            {"type": "input_audio_buffer.commit", "event_id": "commit-0001"},
            ensure_ascii=False,
        )
    )


async def receive_events(ws, timeout_sec: float) -> dict[str, int]:
    counters = {"partial": 0, "final": 0, "error": 0, "other": 0}
    deadline = time.monotonic() + timeout_sec

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        except websockets.ConnectionClosed:
            break

        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            print(f"[recv] non-json: {msg}")
            counters["other"] += 1
            continue

        event_type = data.get("type", "")
        print("[recv]", json.dumps(data, ensure_ascii=False))

        if event_type == "response.output_text.delta":
            counters["partial"] += 1
        elif event_type == "response.output_text.done":
            counters["final"] += 1
        elif event_type == "error":
            counters["error"] += 1
        else:
            counters["other"] += 1

    return counters


async def main() -> int:
    args = parse_args()
    wav_path = Path(args.wav)
    if not wav_path.exists():
        raise FileNotFoundError(f"wav not found: {wav_path}")

    headers = {}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    frames = load_wav_frames(wav_path, args.chunk_ms)
    if not frames:
        raise ValueError("wav has no audio frames")

    print(f"[send] url={args.url} wav={wav_path} chunk_ms={args.chunk_ms} frames={len(frames)}")
    async with websockets.connect(args.url, extra_headers=headers, max_size=8_000_000) as ws:
        await send_audio(ws, frames, args.chunk_ms)
        if not args.skip_response_create:
            await ws.send(json.dumps({"type": "response.create", "event_id": "resp-0001"}))
        counters = await receive_events(ws, args.receive_timeout)

    print(f"[summary] partial={counters['partial']} final={counters['final']} error={counters['error']} other={counters['other']}")
    return 0 if counters["final"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
