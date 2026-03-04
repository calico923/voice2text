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
    transcription_delay_ms: int
    auto_paste: bool

    @staticmethod
    def from_env() -> "AppConfig":
        chunk_ms = int(os.getenv("AUDIO_CHUNK_MS", "20"))
        if chunk_ms not in (20, 40):
            raise ValueError("AUDIO_CHUNK_MS must be 20 or 40")

        return AppConfig(
            server_url=os.getenv("SERVER_URL", "ws://127.0.0.1:8000/v1/realtime"),
            api_key=os.getenv("API_KEY", ""),
            audio_chunk_ms=chunk_ms,
            transcription_delay_ms=int(os.getenv("TRANSCRIPTION_DELAY_MS", "480")),
            auto_paste=_as_bool(os.getenv("AUTO_PASTE"), False),
        )
