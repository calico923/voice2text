from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from transcript_store import TranscriptStore


class TranscriptStoreTest(unittest.TestCase):
    def test_partial_accumulates_for_transcription_delta(self) -> None:
        s = TranscriptStore()
        s.on_event({"type": "transcription.delta", "delta": "a"})
        s.on_event({"type": "transcription.delta", "delta": "b"})
        self.assertEqual("ab", s.partial)

    def test_final_append_for_transcription_done(self) -> None:
        s = TranscriptStore()
        s.on_event(
            {
                "type": "transcription.done",
                "text": "hello",
            }
        )
        self.assertEqual(["hello"], s.finals)

    def test_legacy_final_dedup_by_segment_id(self) -> None:
        s = TranscriptStore()
        s.on_event(
            {
                "type": "response.output_text.done",
                "segment_id": "seg-1",
                "text": "hello",
            }
        )
        self.assertEqual(["hello"], s.finals)

    def test_error_capture(self) -> None:
        s = TranscriptStore()
        s.on_event({"type": "error", "error": "bad", "code": "x"})
        self.assertIn("x", s.last_error)


if __name__ == "__main__":
    unittest.main()
