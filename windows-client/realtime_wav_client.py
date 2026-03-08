#!/usr/bin/env python3
"""Windows validation client for vLLM Realtime API.

This script is intentionally cross-platform so it can be dry-run tested on WSL/Linux.
"""

from __future__ import annotations

import audioop
import argparse
import asyncio
import base64
from collections import deque
import inspect
import json
import math
import os
import shlex
import shutil
import sys
import time
import wave
from pathlib import Path
from typing import Callable

import websockets

DEFAULT_MODEL_ID = "mistralai/Voxtral-Mini-4B-Realtime-2602"
WhichFn = Callable[[str], str | None]
DEFAULT_VAD_SILENCE_MS = 600
DEFAULT_MIN_UTTERANCE_MS = 400
DEFAULT_MAX_UTTERANCE_MS = 6000
DEFAULT_PRE_ROLL_MS = 200
DEFAULT_VAD_RMS_THRESHOLD = 700


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send wav or microphone audio to Realtime API and print events."
    )
    parser.add_argument("--url", required=True, help="e.g. ws://127.0.0.1:8000/v1/realtime")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--wav", help="PCM16/16kHz/mono wav path")
    source.add_argument("--mic", action="store_true", help="Capture from microphone")
    parser.add_argument("--model", default="", help="Model id/path for session.update")
    parser.add_argument("--chunk-ms", type=int, default=20, choices=[20, 40])
    parser.add_argument(
        "--mic-seconds",
        type=float,
        default=30.0,
        help="Seconds to capture when --mic is used",
    )
    parser.add_argument(
        "--mic-device",
        default="",
        help="Input device name/index for the active capture backend",
    )
    parser.add_argument(
        "--capture-cmd",
        default="",
        help="Override microphone capture command. Use {device} placeholder if needed.",
    )
    parser.add_argument(
        "--vad-silence-ms",
        type=int,
        default=DEFAULT_VAD_SILENCE_MS,
        help="Commit microphone utterance after this much trailing silence",
    )
    parser.add_argument(
        "--min-utterance-ms",
        type=int,
        default=DEFAULT_MIN_UTTERANCE_MS,
        help="Do not finalize microphone utterance before this duration",
    )
    parser.add_argument(
        "--max-utterance-ms",
        type=int,
        default=DEFAULT_MAX_UTTERANCE_MS,
        help="Force commit microphone utterance after this duration",
    )
    parser.add_argument(
        "--pre-roll-ms",
        type=int,
        default=DEFAULT_PRE_ROLL_MS,
        help="Keep this much audio before speech onset when VAD starts an utterance",
    )
    parser.add_argument(
        "--vad-rms-threshold",
        type=int,
        default=DEFAULT_VAD_RMS_THRESHOLD,
        help="PCM16 RMS threshold for speech detection in microphone mode",
    )
    parser.add_argument("--receive-timeout", type=float, default=12.0)
    parser.add_argument("--api-key", default="")
    parser.add_argument(
        "--send-response-create",
        action="store_true",
        help="Deprecated. Current vLLM realtime server does not use response.create.",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser


def pcm16_bytes_per_chunk(chunk_ms: int) -> int:
    return int(16000 * chunk_ms / 1000) * 2


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

    bytes_per_chunk = pcm16_bytes_per_chunk(chunk_ms)
    chunks = [pcm[i : i + bytes_per_chunk] for i in range(0, len(pcm), bytes_per_chunk)]
    return [c for c in chunks if c]


def chunk_count_from_duration(duration_sec: float, chunk_ms: int) -> int:
    if duration_sec <= 0:
        raise ValueError("duration_sec must be > 0")
    return max(1, math.ceil((duration_sec * 1000.0) / chunk_ms))


def chunk_count_from_ms(duration_ms: int, chunk_ms: int, *, allow_zero: bool = False) -> int:
    if duration_ms < 0:
        raise ValueError("duration_ms must be >= 0")
    if duration_ms == 0:
        if allow_zero:
            return 0
        raise ValueError("duration_ms must be > 0")
    return max(1, math.ceil(duration_ms / chunk_ms))


def is_speech_chunk(chunk: bytes, rms_threshold: int) -> bool:
    return audioop.rms(chunk, 2) >= rms_threshold


def should_commit_utterance(
    utterance_chunks: int,
    trailing_silence_chunks: int,
    *,
    min_utterance_chunks: int,
    max_utterance_chunks: int,
    vad_silence_chunks: int,
) -> bool:
    if utterance_chunks == 0:
        return False
    if utterance_chunks >= max_utterance_chunks:
        return True
    return (
        utterance_chunks >= min_utterance_chunks and trailing_silence_chunks >= vad_silence_chunks
    )


def build_capture_command(
    platform_name: str,
    device: str = "",
    capture_cmd: str = "",
    which_fn: WhichFn = shutil.which,
) -> list[str]:
    selected_device = device or os.getenv("AUDIO_INPUT_DEVICE", "").strip()
    configured_capture_cmd = capture_cmd or os.getenv("AUDIO_CAPTURE_CMD", "").strip()

    if configured_capture_cmd:
        return shlex.split(configured_capture_cmd.format(device=selected_device))

    if platform_name.startswith("win"):
        if not selected_device:
            raise ValueError(
                "Windows microphone capture requires --mic-device or AUDIO_INPUT_DEVICE, "
                "or set --capture-cmd."
            )
        if which_fn("ffmpeg"):
            return [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "dshow",
                "-i",
                f"audio={selected_device}",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "pipe:1",
            ]
        raise RuntimeError(
            "ffmpeg is required for Windows microphone capture, or set --capture-cmd"
        )

    if platform_name == "darwin":
        selected_device = selected_device or "0"
        if which_fn("ffmpeg"):
            return [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "avfoundation",
                "-i",
                f":{selected_device}",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "pipe:1",
            ]
        raise RuntimeError(
            "ffmpeg is required for macOS microphone capture, or set --capture-cmd"
        )

    if platform_name.startswith("linux"):
        if which_fn("arecord"):
            command = [
                "arecord",
                "-q",
                "-f",
                "S16_LE",
                "-c",
                "1",
                "-r",
                "16000",
                "-t",
                "raw",
            ]
            if selected_device:
                command.extend(["-D", selected_device])
            command.append("-")
            return command
        raise RuntimeError(
            "arecord is required for Linux microphone capture, or set --capture-cmd"
        )

    raise RuntimeError(
        f"unsupported microphone capture platform: {platform_name}. Set --capture-cmd."
    )


async def send_audio_chunk(ws, chunk: bytes) -> None:
    event = {
        "type": "input_audio_buffer.append",
        "audio": base64.b64encode(chunk).decode("ascii"),
    }
    await ws.send(json.dumps(event, ensure_ascii=False))


async def send_commit_sequence(ws) -> None:
    await ws.send(json.dumps({"type": "input_audio_buffer.commit"}, ensure_ascii=False))
    await ws.send(
        json.dumps({"type": "input_audio_buffer.commit", "final": True}, ensure_ascii=False)
    )


async def send_wav_stream(ws, chunks: list[bytes], chunk_ms: int) -> int:
    for chunk in chunks:
        await send_audio_chunk(ws, chunk)
        await asyncio.sleep(chunk_ms / 1000.0)

    await send_commit_sequence(ws)
    return len(chunks)


async def stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


async def send_mic_stream(
    ws,
    chunk_ms: int,
    duration_sec: float,
    device: str,
    capture_cmd: str,
    vad_silence_ms: int,
    min_utterance_ms: int,
    max_utterance_ms: int,
    pre_roll_ms: int,
    vad_rms_threshold: int,
) -> tuple[int, list[str], int]:
    if vad_silence_ms <= 0:
        raise ValueError("--vad-silence-ms must be > 0")
    if min_utterance_ms <= 0:
        raise ValueError("--min-utterance-ms must be > 0")
    if max_utterance_ms < min_utterance_ms:
        raise ValueError("--max-utterance-ms must be >= --min-utterance-ms")
    if pre_roll_ms < 0:
        raise ValueError("--pre-roll-ms must be >= 0")
    if vad_rms_threshold <= 0:
        raise ValueError("--vad-rms-threshold must be > 0")

    command = build_capture_command(
        platform_name=sys.platform,
        device=device,
        capture_cmd=capture_cmd,
    )
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    sent = 0
    segments = 0
    in_utterance = False
    utterance_chunks = 0
    trailing_silence_chunks = 0
    max_capture_chunks = chunk_count_from_duration(duration_sec, chunk_ms)
    vad_silence_chunks = chunk_count_from_ms(vad_silence_ms, chunk_ms)
    min_utterance_chunks = chunk_count_from_ms(min_utterance_ms, chunk_ms)
    max_utterance_chunks = chunk_count_from_ms(max_utterance_ms, chunk_ms)
    pre_roll_chunks = chunk_count_from_ms(pre_roll_ms, chunk_ms, allow_zero=True)
    pre_roll_buffer: deque[bytes] = deque(maxlen=pre_roll_chunks if pre_roll_chunks > 0 else 1)

    try:
        for _ in range(max_capture_chunks):
            if process.stdout is None:
                raise RuntimeError("capture process stdout is not available")
            try:
                chunk = await process.stdout.readexactly(pcm16_bytes_per_chunk(chunk_ms))
            except asyncio.IncompleteReadError as exc:
                chunk = exc.partial
            if not chunk:
                break

            if not in_utterance:
                if pre_roll_chunks:
                    pre_roll_buffer.append(chunk)
                if not is_speech_chunk(chunk, vad_rms_threshold):
                    continue

                in_utterance = True
                utterance_chunks = 0
                trailing_silence_chunks = 0
                buffered_chunks = list(pre_roll_buffer) if pre_roll_chunks else [chunk]
                pre_roll_buffer.clear()
                for buffered_chunk in buffered_chunks:
                    await send_audio_chunk(ws, buffered_chunk)
                    sent += 1
                    utterance_chunks += 1
                continue

            await send_audio_chunk(ws, chunk)
            sent += 1
            utterance_chunks += 1
            if is_speech_chunk(chunk, vad_rms_threshold):
                trailing_silence_chunks = 0
            else:
                trailing_silence_chunks += 1

            if should_commit_utterance(
                utterance_chunks,
                trailing_silence_chunks,
                min_utterance_chunks=min_utterance_chunks,
                max_utterance_chunks=max_utterance_chunks,
                vad_silence_chunks=vad_silence_chunks,
            ):
                await send_commit_sequence(ws)
                segments += 1
                in_utterance = False
                utterance_chunks = 0
                trailing_silence_chunks = 0
                pre_roll_buffer.clear()
    finally:
        await stop_process(process)

    if sent == 0:
        raise RuntimeError("microphone capture produced no audio chunks")

    if in_utterance and utterance_chunks > 0:
        await send_commit_sequence(ws)
        segments += 1

    return sent, command, segments


def normalize_result_counters() -> dict[str, int]:
    return {
        "partial": 0,
        "final": 0,
        "error": 0,
        "other": 0,
    }


def classify_event(event_type: str) -> str:
    if event_type in {"transcription.delta", "response.output_text.delta"}:
        return "partial"
    if event_type in {"transcription.done", "response.output_text.done"}:
        return "final"
    if event_type == "error":
        return "error"
    return "other"


async def receive_stream(ws, total_timeout_sec: float, pretty: bool) -> dict[str, int]:
    counters = normalize_result_counters()
    deadline = time.monotonic() + total_timeout_sec

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


def estimate_send_duration_sec(args: argparse.Namespace, chunk_count: int = 0) -> float:
    if args.wav:
        return chunk_count * args.chunk_ms / 1000.0
    return args.mic_seconds


def describe_source(args: argparse.Namespace) -> str:
    if args.wav:
        return args.wav
    return f"mic:{args.mic_device or os.getenv('AUDIO_INPUT_DEVICE', 'default')}"


async def run(args: argparse.Namespace) -> int:
    chunks: list[bytes] = []
    if args.wav:
        wav_path = Path(args.wav)
        if not wav_path.exists():
            raise FileNotFoundError(f"WAV not found: {wav_path}")
        chunks = load_wav(wav_path, args.chunk_ms)
    elif args.mic_seconds <= 0:
        raise ValueError("--mic-seconds must be > 0")

    headers = {}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    source_duration_sec = estimate_send_duration_sec(args, len(chunks))
    print(
        f"[info] url={args.url} source={describe_source(args)} chunk_ms={args.chunk_ms} "
        f"duration_sec={source_duration_sec:.2f} model={args.model or DEFAULT_MODEL_ID}"
    )
    if args.mic:
        print(
            "[vad] "
            f"silence_ms={args.vad_silence_ms} "
            f"min_utterance_ms={args.min_utterance_ms} "
            f"max_utterance_ms={args.max_utterance_ms} "
            f"pre_roll_ms={args.pre_roll_ms} "
            f"rms_threshold={args.vad_rms_threshold}"
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
                {
                    "type": "session.update",
                    "model": args.model or DEFAULT_MODEL_ID,
                },
                ensure_ascii=False,
            )
        )
        receive_task = asyncio.create_task(
            receive_stream(
                ws,
                total_timeout_sec=args.receive_timeout + source_duration_sec + 1.0,
                pretty=args.pretty,
            )
        )
        try:
            if args.wav:
                sent_chunks = await send_wav_stream(ws, chunks, args.chunk_ms)
                segment_count = 1 if sent_chunks else 0
            else:
                sent_chunks, command, segment_count = await send_mic_stream(
                    ws,
                    chunk_ms=args.chunk_ms,
                    duration_sec=args.mic_seconds,
                    device=args.mic_device,
                    capture_cmd=args.capture_cmd,
                    vad_silence_ms=args.vad_silence_ms,
                    min_utterance_ms=args.min_utterance_ms,
                    max_utterance_ms=args.max_utterance_ms,
                    pre_roll_ms=args.pre_roll_ms,
                    vad_rms_threshold=args.vad_rms_threshold,
                )
                print(f"[capture] backend={' '.join(command)}")
        except Exception:
            receive_task.cancel()
            raise

        counters = await receive_task

    print(
        f"[summary] {json.dumps(counters, ensure_ascii=False)} "
        f"sent_chunks={sent_chunks} segments={segment_count}"
    )
    return 0 if counters["final"] > 0 else 2


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
