#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from audio_capture import AudioCapture, chunk_count_from_duration
from audio_frame import load_wav_as_pcm16_mono_16k, split_pcm16_into_chunks
from config import AppConfig
from logger import JsonlLogger
from paste_controller import PasteController
from reconnect_controller import ReconnectController
from realtime_client import RealtimeClient
from transcript_store import TranscriptStore

PARTIAL_EVENT_TYPES = {"transcription.delta", "response.output_text.delta"}
FINAL_EVENT_TYPES = {"transcription.done", "response.output_text.done"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mac CLI realtime client")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--wav", help="WAV file path for initial E2E")
    source.add_argument("--mic", action="store_true", help="Capture from the default microphone")
    p.add_argument("--url", default="")
    p.add_argument("--model", default="")
    p.add_argument("--chunk-ms", type=int, default=0)
    p.add_argument(
        "--mic-seconds",
        type=float,
        default=5.0,
        help="Seconds to capture when --mic is used",
    )
    p.add_argument(
        "--mic-device",
        default="",
        help="Input device index/name for the active capture backend",
    )
    p.add_argument("--receive-timeout", type=float, default=12.0)
    p.add_argument(
        "--no-response-create",
        action="store_true",
        help="Deprecated. Current vLLM realtime server does not use response.create.",
    )
    return p.parse_args()


async def send_wav_input(
    client: RealtimeClient,
    logger: JsonlLogger,
    wav_path: Path,
    chunk_ms: int,
) -> None:
    pcm16 = load_wav_as_pcm16_mono_16k(wav_path)
    chunks = split_pcm16_into_chunks(pcm16, chunk_ms)
    for i, chunk in enumerate(chunks, 1):
        await client.send_append(chunk, f"append-{i:05d}")
        logger.log("send_append", index=i, size=len(chunk), source="wav")
        await asyncio.sleep(chunk_ms / 1000.0)


async def send_mic_input(
    client: RealtimeClient,
    logger: JsonlLogger,
    chunk_ms: int,
    duration_sec: float,
    device: str,
) -> None:
    capture = AudioCapture(chunk_ms=chunk_ms, device=device)
    await capture.start()
    logger.log(
        "capture_start",
        backend=(capture.command[0] if capture.command else ""),
        device=device or "default",
        duration_sec=duration_sec,
    )

    sent = 0
    try:
        async for chunk in capture.iter_chunks(
            max_chunks=chunk_count_from_duration(duration_sec, chunk_ms)
        ):
            sent += 1
            await client.send_append(chunk, f"append-{sent:05d}")
            logger.log("send_append", index=sent, size=len(chunk), source="mic")
    finally:
        await capture.stop()
        logger.log("capture_stop", chunks_sent=sent)

    if sent == 0:
        raise RuntimeError("microphone capture produced no audio chunks")


async def run() -> int:
    args = parse_args()
    cfg = AppConfig.from_env()

    url = args.url or cfg.server_url
    chunk_ms = args.chunk_ms or cfg.audio_chunk_ms
    if args.mic and args.mic_seconds <= 0:
        raise ValueError("--mic-seconds must be > 0")

    client = RealtimeClient(url=url, api_key=cfg.api_key, model=args.model)
    store = TranscriptStore()
    logger = JsonlLogger(enabled=cfg.log_to_file, path=cfg.log_file)
    reconnect = ReconnectController()
    paste = PasteController(
        enabled=cfg.auto_paste,
        min_interval_ms=cfg.paste_min_interval_ms,
    )

    commit_sent_at = 0.0
    await client.connect()
    reconnect.reset()
    logger.log("connect", server_url=url)
    try:
        await client.send_session_update()
        logger.log("send_session_update", model=args.model or client.model or "default")
        if args.wav:
            wav_path = Path(args.wav)
            if not wav_path.exists():
                raise FileNotFoundError(f"wav not found: {wav_path}")
            await send_wav_input(client, logger, wav_path, chunk_ms)
        else:
            await send_mic_input(
                client,
                logger,
                chunk_ms=chunk_ms,
                duration_sec=args.mic_seconds,
                device=args.mic_device,
            )
        await client.send_commit()
        commit_sent_at = time.monotonic()
        logger.log("send_commit")
        await client.send_commit(event_id="commit-final-0002", final=True)
        logger.log("send_commit_final")

        async for event in client.iter_events(timeout_sec=args.receive_timeout):
            store.on_event(event)
            et = event.get("type", "")
            logger.log("recv_event", received_type=et)
            if et in PARTIAL_EVENT_TYPES:
                print(f"\rpartial: {store.partial}", end="", flush=True)
            elif et in FINAL_EVENT_TYPES:
                print(f"\nfinal: {store.finals[-1]}")
                latency_ms = int((time.monotonic() - commit_sent_at) * 1000) if commit_sent_at else -1
                logger.log("final_text", text=store.finals[-1], latency_ms=latency_ms)
                pasted, reason = paste.paste(store.finals[-1])
                if cfg.auto_paste:
                    print(f"paste: {reason}")
                logger.log("paste", enabled=cfg.auto_paste, result=reason, pasted=pasted)
            elif et == "session.created":
                logger.log("session_created", session_id=event.get("id", ""))
            elif et == "error":
                print(f"\nerror: {store.last_error}")
                logger.log("error", error=store.last_error)
            else:
                print(f"\nevent: {event}")
                logger.log("other_event", payload=event)
    finally:
        await client.close()
        logger.log("disconnect", next_reconnect_delay_sec=reconnect.next_delay_sec())

    print(
        f"\nsummary: finals={len(store.finals)} partial_present={bool(store.partial)} error={store.last_error or '-'}"
    )
    return 0 if store.finals else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
