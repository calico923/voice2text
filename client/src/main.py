#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from audio_frame import load_wav_as_pcm16_mono_16k, split_pcm16_into_chunks
from config import AppConfig
from logger import JsonlLogger
from paste_controller import PasteController
from reconnect_controller import ReconnectController
from realtime_client import RealtimeClient
from transcript_store import TranscriptStore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mac CLI realtime client (wav mode)")
    p.add_argument("--wav", required=True, help="WAV file path for initial E2E")
    p.add_argument("--url", default="")
    p.add_argument("--model", default="")
    p.add_argument("--chunk-ms", type=int, default=0)
    p.add_argument("--receive-timeout", type=float, default=12.0)
    p.add_argument(
        "--no-response-create",
        action="store_true",
        help="Deprecated. Current vLLM realtime server does not use response.create.",
    )
    return p.parse_args()


async def run() -> int:
    args = parse_args()
    cfg = AppConfig.from_env()

    url = args.url or cfg.server_url
    chunk_ms = args.chunk_ms or cfg.audio_chunk_ms

    wav_path = Path(args.wav)
    if not wav_path.exists():
        raise FileNotFoundError(f"wav not found: {wav_path}")

    pcm16 = load_wav_as_pcm16_mono_16k(wav_path)
    chunks = split_pcm16_into_chunks(pcm16, chunk_ms)

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
        for i, chunk in enumerate(chunks, 1):
            await client.send_append(chunk, f"append-{i:05d}")
            logger.log("send_append", index=i, size=len(chunk))
            await asyncio.sleep(chunk_ms / 1000.0)
        await client.send_commit()
        commit_sent_at = time.monotonic()
        logger.log("send_commit")
        await client.send_commit(event_id="commit-final-0002", final=True)
        logger.log("send_commit_final")

        async for event in client.iter_events(timeout_sec=args.receive_timeout):
            store.on_event(event)
            et = event.get("type", "")
            logger.log("recv_event", received_type=et)
            if et == "transcription.delta":
                print(f"\rpartial: {store.partial}", end="", flush=True)
            elif et == "transcription.done":
                print(f"\nfinal: {store.finals[-1]}")
                latency_ms = int((time.monotonic() - commit_sent_at) * 1000) if commit_sent_at else -1
                logger.log("final_text", text=store.finals[-1], latency_ms=latency_ms)
                pasted, reason = paste.paste(store.finals[-1])
                if cfg.auto_paste:
                    print(f"paste: {reason}")
                logger.log("paste", enabled=cfg.auto_paste, result=reason, pasted=pasted)
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
