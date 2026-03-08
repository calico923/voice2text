from __future__ import annotations

import audioop
import wave
from pathlib import Path


def normalize_to_pcm16_mono_16k(
    raw: bytes, sample_width: int, channels: int, sample_rate: int
) -> bytes:
    pcm16 = raw
    width = sample_width

    if width != 2:
        pcm16 = audioop.lin2lin(pcm16, width, 2)
        width = 2

    if channels == 2:
        pcm16 = audioop.tomono(pcm16, width, 0.5, 0.5)
    elif channels != 1:
        raise ValueError(f"unsupported channels: {channels}")

    if sample_rate != 16000:
        pcm16, _ = audioop.ratecv(pcm16, width, 1, sample_rate, 16000, None)

    return pcm16


def load_wav_as_pcm16_mono_16k(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    return normalize_to_pcm16_mono_16k(raw, sample_width, channels, sample_rate)


def pcm16_bytes_per_chunk(chunk_ms: int) -> int:
    if chunk_ms not in (20, 40):
        raise ValueError("chunk_ms must be 20 or 40")
    return int(16000 * chunk_ms / 1000) * 2


def split_pcm16_into_chunks(pcm16: bytes, chunk_ms: int) -> list[bytes]:
    bytes_per_chunk = pcm16_bytes_per_chunk(chunk_ms)
    return [
        pcm16[i : i + bytes_per_chunk]
        for i in range(0, len(pcm16), bytes_per_chunk)
        if pcm16[i : i + bytes_per_chunk]
    ]
