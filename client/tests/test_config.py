from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from config import AppConfig


class ConfigTest(unittest.TestCase):
    def test_defaults_include_conversation_settings(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig.from_env()
        self.assertEqual(20, cfg.audio_chunk_ms)
        self.assertEqual(120, cfg.partial_flush_ms)
        self.assertEqual(600, cfg.vad_silence_ms)
        self.assertEqual(400, cfg.min_utterance_ms)
        self.assertEqual(6000, cfg.max_utterance_ms)
        self.assertEqual(200, cfg.pre_roll_ms)
        self.assertEqual(700, cfg.vad_rms_threshold)

    def test_partial_flush_falls_back_to_legacy_env(self) -> None:
        with patch.dict(os.environ, {"TRANSCRIPTION_DELAY_MS": "150"}, clear=True):
            cfg = AppConfig.from_env()
        self.assertEqual(150, cfg.partial_flush_ms)


if __name__ == "__main__":
    unittest.main()
