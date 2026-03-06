#!/usr/bin/env python3
"""Local smoke client for vLLM Realtime API."""

from __future__ import annotations

import argparse
import asyncio
import base64
import inspect
import json
import os
import time
import wave
from pathlib import Path

import websockets

DEFAULT_MODEL_ID = "mistralai/Voxtral-Mini-4B-Realtime-2602"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Realtime local smoke client")
    parser.add_argument("--url", default="ws://127.0.0.1:8000/v1/realtime")
    parser.add_argument("--wav", required=True, help="PCM16/16kHz/mono wav path")
    parser.add_argument("--model", default="", help="Model id/path for session.update")
    parser.add_argument("--chunk-ms", type=int, default=20, choices=[20, 40])
    parser.add_argument("--api-key", default="", help="Optional bearer token")
    parser.add_argument("--receive-timeout", type=float, default=8.0)
    parser.add_argument(
        "--skip-response-create",
        action="store_true",
        help="Deprecated. Current vLLM realtime server does not use response.create.",
    )
    return parser.parse_args()


def read_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        current_key, value = line.split("=", 1)
        if current_key != key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value

    return ""


def resolve_model_id(explicit_model: str) -> str:
    if explicit_model:
        return explicit_model

    env_model = os.getenv("MODEL_ID", "").strip()
    if env_model:
        return env_model

    local_env_model = read_env_value(Path("server/.env"), "MODEL_ID")
    if local_env_model:
        return local_env_model

    return DEFAULT_MODEL_ID


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
    for frame in frames:
        payload = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(frame).decode("ascii"),
        }
        await ws.send(json.dumps(payload, ensure_ascii=False))
        await asyncio.sleep(chunk_ms / 1000.0)

    # First commit starts generation, then final=True closes the audio stream.
    await ws.send(json.dumps({"type": "input_audio_buffer.commit"}, ensure_ascii=False))
    await ws.send(
        json.dumps({"type": "input_audio_buffer.commit", "final": True}, ensure_ascii=False)
    )


async def receive_events(ws, timeout_sec: float) -> tuple[dict[str, int], str]:
    counters = {"partial": 0, "empty_partial": 0, "final": 0, "error": 0, "other": 0}
    deadline = time.monotonic() + timeout_sec
    final_text = ""

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

        if event_type == "transcription.delta":
            if str(data.get("delta", "")):
                counters["partial"] += 1
            else:
                counters["empty_partial"] += 1
        elif event_type == "transcription.done":
            counters["final"] += 1
            final_text = str(data.get("text", "")).strip()
        elif event_type == "error":
            counters["error"] += 1
        else:
            counters["other"] += 1

    return counters, final_text


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

    model_id = resolve_model_id(args.model)
    print(
        f"[send] url={args.url} wav={wav_path} chunk_ms={args.chunk_ms} "
        f"frames={len(frames)} model={model_id}"
    )
    connect_kwargs = {"max_size": 8_000_000}
    if headers:
        params = inspect.signature(websockets.connect).parameters
        if "additional_headers" in params:
            connect_kwargs["additional_headers"] = headers
        else:
            connect_kwargs["extra_headers"] = headers

    async with websockets.connect(args.url, **connect_kwargs) as ws:
        await ws.send(
            json.dumps(
                {"type": "session.update", "model": model_id},
                ensure_ascii=False,
            )
        )
        await send_audio(ws, frames, args.chunk_ms)
        counters, final_text = await receive_events(ws, args.receive_timeout)

    print(
        "[summary] "
        f"partial={counters['partial']} "
        f"empty_partial={counters['empty_partial']} "
        f"final={counters['final']} "
        f"error={counters['error']} "
        f"other={counters['other']} "
        f'final_text="{final_text}"'
    )
    return 0 if counters["final"] > 0 and counters["error"] == 0 and final_text else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
