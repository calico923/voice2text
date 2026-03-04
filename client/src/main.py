#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from audio_frame import load_wav_as_pcm16_mono_16k, split_pcm16_into_chunks
from config import AppConfig
from paste_controller import PasteController
from realtime_client import RealtimeClient
from transcript_store import TranscriptStore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mac CLI realtime client (wav mode)")
    p.add_argument("--wav", required=True, help="WAV file path for initial E2E")
    p.add_argument("--url", default="")
    p.add_argument("--chunk-ms", type=int, default=0)
    p.add_argument("--receive-timeout", type=float, default=12.0)
    p.add_argument("--no-response-create", action="store_true")
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

    client = RealtimeClient(url=url, api_key=cfg.api_key)
    store = TranscriptStore()
    paste = PasteController(
        enabled=cfg.auto_paste,
        min_interval_ms=cfg.paste_min_interval_ms,
    )

    await client.connect()
    try:
        for i, chunk in enumerate(chunks, 1):
            await client.send_append(chunk, f"append-{i:05d}")
            await asyncio.sleep(chunk_ms / 1000.0)
        await client.send_commit()
        if not args.no_response_create:
            await client.send_response_create()

        async for event in client.iter_events(timeout_sec=args.receive_timeout):
            store.on_event(event)
            et = event.get("type", "")
            if et == "response.output_text.delta":
                print(f"\rpartial: {store.partial}", end="", flush=True)
            elif et == "response.output_text.done":
                print(f"\nfinal: {store.finals[-1]}")
                pasted, reason = paste.paste(store.finals[-1])
                if cfg.auto_paste:
                    print(f"paste: {reason}")
            elif et == "error":
                print(f"\nerror: {store.last_error}")
            else:
                print(f"\nevent: {event}")
    finally:
        await client.close()

    print(
        f"\nsummary: finals={len(store.finals)} partial_present={bool(store.partial)} error={store.last_error or '-'}"
    )
    return 0 if store.finals else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
