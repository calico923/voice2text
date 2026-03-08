#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import time
from collections import deque
from pathlib import Path

from audio_capture import (
    AudioCapture,
    chunk_count_from_duration,
    chunk_count_from_ms,
    is_speech_chunk,
    should_commit_utterance,
)
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
        default=30.0,
        help="Seconds to capture when --mic is used",
    )
    p.add_argument(
        "--mic-device",
        default="",
        help="Input device index/name for the active capture backend",
    )
    p.add_argument(
        "--partial-flush-ms",
        type=int,
        default=None,
        help="Throttle interval for partial transcript display",
    )
    p.add_argument(
        "--vad-silence-ms",
        type=int,
        default=None,
        help="Commit microphone utterance after this much trailing silence",
    )
    p.add_argument(
        "--min-utterance-ms",
        type=int,
        default=None,
        help="Do not finalize microphone utterance before this duration",
    )
    p.add_argument(
        "--max-utterance-ms",
        type=int,
        default=None,
        help="Force commit microphone utterance after this duration",
    )
    p.add_argument(
        "--pre-roll-ms",
        type=int,
        default=None,
        help="Keep this much audio before speech onset when VAD starts an utterance",
    )
    p.add_argument(
        "--vad-rms-threshold",
        type=int,
        default=None,
        help="PCM16 RMS threshold for microphone speech detection",
    )
    p.add_argument("--receive-timeout", type=float, default=12.0)
    p.add_argument(
        "--no-response-create",
        action="store_true",
        help="Deprecated. Current vLLM realtime server does not use response.create.",
    )
    return p.parse_args()


async def send_commit_sequence(
    client: RealtimeClient,
    logger: JsonlLogger,
    commit_sent_ats: deque[float],
) -> None:
    await client.send_commit()
    commit_sent_ats.append(time.monotonic())
    logger.log("send_commit")
    await client.send_commit(event_id="commit-final-0002", final=True)
    logger.log("send_commit_final")


async def send_wav_input(
    client: RealtimeClient,
    logger: JsonlLogger,
    wav_path: Path,
    chunk_ms: int,
    commit_sent_ats: deque[float],
) -> tuple[int, int]:
    pcm16 = load_wav_as_pcm16_mono_16k(wav_path)
    chunks = split_pcm16_into_chunks(pcm16, chunk_ms)
    for i, chunk in enumerate(chunks, 1):
        await client.send_append(chunk, f"append-{i:05d}")
        logger.log("send_append", index=i, size=len(chunk), source="wav")
        await asyncio.sleep(chunk_ms / 1000.0)
    await send_commit_sequence(client, logger, commit_sent_ats)
    return len(chunks), 1 if chunks else 0


async def send_mic_input(
    client: RealtimeClient,
    logger: JsonlLogger,
    chunk_ms: int,
    duration_sec: float,
    device: str,
    *,
    vad_silence_ms: int,
    min_utterance_ms: int,
    max_utterance_ms: int,
    pre_roll_ms: int,
    vad_rms_threshold: int,
    commit_sent_ats: deque[float],
) -> tuple[int, int]:
    capture = AudioCapture(chunk_ms=chunk_ms, device=device)
    await capture.start()
    logger.log(
        "capture_start",
        backend=(capture.command[0] if capture.command else ""),
        device=device or "default",
        duration_sec=duration_sec,
        vad_silence_ms=vad_silence_ms,
        min_utterance_ms=min_utterance_ms,
        max_utterance_ms=max_utterance_ms,
        pre_roll_ms=pre_roll_ms,
        vad_rms_threshold=vad_rms_threshold,
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
        async for chunk in capture.iter_chunks(max_chunks=max_capture_chunks):
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
                    sent += 1
                    utterance_chunks += 1
                    await client.send_append(buffered_chunk, f"append-{sent:05d}")
                    logger.log("send_append", index=sent, size=len(buffered_chunk), source="mic")
                continue

            sent += 1
            utterance_chunks += 1
            await client.send_append(chunk, f"append-{sent:05d}")
            logger.log("send_append", index=sent, size=len(chunk), source="mic")
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
                reason = (
                    "max_duration"
                    if utterance_chunks >= max_utterance_chunks
                    else "vad_silence"
                )
                await send_commit_sequence(client, logger, commit_sent_ats)
                segments += 1
                logger.log(
                    "utterance_commit",
                    reason=reason,
                    utterance_chunks=utterance_chunks,
                    trailing_silence_chunks=trailing_silence_chunks,
                )
                in_utterance = False
                utterance_chunks = 0
                trailing_silence_chunks = 0
                pre_roll_buffer.clear()
    finally:
        await capture.stop()
        logger.log("capture_stop", chunks_sent=sent, segments=segments)

    if sent == 0:
        raise RuntimeError("microphone capture produced no audio chunks")

    if in_utterance and utterance_chunks > 0:
        await send_commit_sequence(client, logger, commit_sent_ats)
        segments += 1
        logger.log("utterance_commit", reason="stream_end", utterance_chunks=utterance_chunks)

    if segments == 0:
        raise RuntimeError("microphone capture produced no finalized utterance")

    return sent, segments


async def receive_events(
    client: RealtimeClient,
    store: TranscriptStore,
    logger: JsonlLogger,
    paste: PasteController,
    *,
    partial_flush_ms: int,
    receive_timeout: float,
    auto_paste_enabled: bool,
    send_done: asyncio.Event,
    commit_sent_ats: deque[float],
) -> None:
    post_send_deadline: float | None = None
    last_partial_print_at = 0.0

    while True:
        now = time.monotonic()
        if send_done.is_set():
            if post_send_deadline is None:
                post_send_deadline = now + receive_timeout
            remaining = post_send_deadline - now
            if remaining <= 0:
                break
            timeout_sec = min(0.25, remaining)
        else:
            timeout_sec = 0.25

        event = await client.recv_event(timeout_sec=timeout_sec)
        if event is None:
            continue

        et = event.get("type", "")
        if et == "connection.closed":
            break

        if send_done.is_set():
            post_send_deadline = time.monotonic() + receive_timeout

        finals_before = len(store.finals)
        store.on_event(event)
        logger.log("recv_event", received_type=et)

        if et in PARTIAL_EVENT_TYPES:
            now = time.monotonic()
            if now - last_partial_print_at >= (partial_flush_ms / 1000.0):
                print(f"\rpartial: {store.partial}", end="", flush=True)
                last_partial_print_at = now
            continue

        if et in FINAL_EVENT_TYPES:
            commit_sent_at = commit_sent_ats.popleft() if commit_sent_ats else 0.0
            if len(store.finals) == finals_before:
                logger.log("final_text_empty")
                continue
            print(f"\nfinal: {store.finals[-1]}")
            latency_ms = int((time.monotonic() - commit_sent_at) * 1000) if commit_sent_at else -1
            logger.log("final_text", text=store.finals[-1], latency_ms=latency_ms)
            pasted, reason = paste.paste(store.finals[-1])
            if auto_paste_enabled:
                print(f"paste: {reason}")
            logger.log("paste", enabled=auto_paste_enabled, result=reason, pasted=pasted)
            continue

        if et == "session.created":
            logger.log("session_created", session_id=event.get("id", ""))
            continue

        if et == "error":
            print(f"\nerror: {store.last_error}")
            logger.log("error", error=store.last_error)
            continue

        print(f"\nevent: {event}")
        logger.log("other_event", payload=event)


async def run() -> int:
    args = parse_args()
    cfg = AppConfig.from_env()

    url = args.url or cfg.server_url
    chunk_ms = args.chunk_ms or cfg.audio_chunk_ms
    partial_flush_ms = args.partial_flush_ms or cfg.partial_flush_ms
    vad_silence_ms = args.vad_silence_ms or cfg.vad_silence_ms
    min_utterance_ms = args.min_utterance_ms or cfg.min_utterance_ms
    max_utterance_ms = args.max_utterance_ms or cfg.max_utterance_ms
    pre_roll_ms = cfg.pre_roll_ms if args.pre_roll_ms is None else args.pre_roll_ms
    vad_rms_threshold = args.vad_rms_threshold or cfg.vad_rms_threshold

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
    commit_sent_ats: deque[float] = deque()
    send_done = asyncio.Event()
    receiver_task: asyncio.Task | None = None
    sent_chunks = 0
    segment_count = 0

    await client.connect()
    reconnect.reset()
    logger.log("connect", server_url=url)
    receiver_task = asyncio.create_task(
        receive_events(
            client,
            store,
            logger,
            paste,
            partial_flush_ms=partial_flush_ms,
            receive_timeout=args.receive_timeout,
            auto_paste_enabled=cfg.auto_paste,
            send_done=send_done,
            commit_sent_ats=commit_sent_ats,
        )
    )
    try:
        await client.send_session_update()
        logger.log("send_session_update", model=args.model or client.model or "default")
        if args.wav:
            wav_path = Path(args.wav)
            if not wav_path.exists():
                raise FileNotFoundError(f"wav not found: {wav_path}")
            sent_chunks, segment_count = await send_wav_input(
                client,
                logger,
                wav_path,
                chunk_ms,
                commit_sent_ats,
            )
        else:
            sent_chunks, segment_count = await send_mic_input(
                client,
                logger,
                chunk_ms=chunk_ms,
                duration_sec=args.mic_seconds,
                device=args.mic_device,
                vad_silence_ms=vad_silence_ms,
                min_utterance_ms=min_utterance_ms,
                max_utterance_ms=max_utterance_ms,
                pre_roll_ms=pre_roll_ms,
                vad_rms_threshold=vad_rms_threshold,
                commit_sent_ats=commit_sent_ats,
            )
        send_done.set()
        await receiver_task
    finally:
        if not send_done.is_set():
            send_done.set()
        if receiver_task is not None and not receiver_task.done():
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass
        await client.close()
        logger.log("disconnect", next_reconnect_delay_sec=reconnect.next_delay_sec())

    print(
        f"\nsummary: finals={len(store.finals)} partial_present={bool(store.partial)} "
        f"error={store.last_error or '-'} sent_chunks={sent_chunks} segments={segment_count}"
    )
    return 0 if store.finals else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
