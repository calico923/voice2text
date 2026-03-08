from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(raw: str, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AppConfig:
    server_url: str
    api_key: str
    audio_chunk_ms: int
    partial_flush_ms: int
    vad_silence_ms: int
    min_utterance_ms: int
    max_utterance_ms: int
    pre_roll_ms: int
    vad_rms_threshold: int
    auto_paste: bool
    paste_min_interval_ms: int
    log_to_file: bool
    log_file: str

    @staticmethod
    def from_env() -> "AppConfig":
        chunk_ms = int(os.getenv("AUDIO_CHUNK_MS", "20"))
        if chunk_ms not in (20, 40):
            raise ValueError("AUDIO_CHUNK_MS must be 20 or 40")

        partial_flush_ms = int(
            os.getenv("PARTIAL_FLUSH_MS", os.getenv("TRANSCRIPTION_DELAY_MS", "120"))
        )
        vad_silence_ms = int(os.getenv("VAD_SILENCE_MS", "600"))
        min_utterance_ms = int(os.getenv("MIN_UTTERANCE_MS", "400"))
        max_utterance_ms = int(os.getenv("MAX_UTTERANCE_MS", "6000"))
        pre_roll_ms = int(os.getenv("PRE_ROLL_MS", "200"))
        vad_rms_threshold = int(os.getenv("VAD_RMS_THRESHOLD", "700"))

        if partial_flush_ms <= 0:
            raise ValueError("PARTIAL_FLUSH_MS must be > 0")
        if vad_silence_ms <= 0:
            raise ValueError("VAD_SILENCE_MS must be > 0")
        if min_utterance_ms <= 0:
            raise ValueError("MIN_UTTERANCE_MS must be > 0")
        if max_utterance_ms < min_utterance_ms:
            raise ValueError("MAX_UTTERANCE_MS must be >= MIN_UTTERANCE_MS")
        if pre_roll_ms < 0:
            raise ValueError("PRE_ROLL_MS must be >= 0")
        if vad_rms_threshold <= 0:
            raise ValueError("VAD_RMS_THRESHOLD must be > 0")

        return AppConfig(
            server_url=os.getenv("SERVER_URL", "ws://127.0.0.1:8000/v1/realtime"),
            api_key=os.getenv("API_KEY", ""),
            audio_chunk_ms=chunk_ms,
            partial_flush_ms=partial_flush_ms,
            vad_silence_ms=vad_silence_ms,
            min_utterance_ms=min_utterance_ms,
            max_utterance_ms=max_utterance_ms,
            pre_roll_ms=pre_roll_ms,
            vad_rms_threshold=vad_rms_threshold,
            auto_paste=_as_bool(os.getenv("AUTO_PASTE"), False),
            paste_min_interval_ms=int(os.getenv("PASTE_MIN_INTERVAL_MS", "700")),
            log_to_file=_as_bool(os.getenv("LOG_TO_FILE"), False),
            log_file=os.getenv("LOG_FILE", "client/logs/events.jsonl"),
        )
