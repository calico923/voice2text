from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from transcript_store import TranscriptStore


class TranscriptStoreTest(unittest.TestCase):
    def test_partial_overwrite(self) -> None:
        s = TranscriptStore()
        s.on_event({"type": "response.output_text.delta", "delta": "a"})
        s.on_event({"type": "response.output_text.delta", "delta": "ab"})
        self.assertEqual("ab", s.partial)

    def test_final_append_and_dedup(self) -> None:
        s = TranscriptStore()
        s.on_event(
            {
                "type": "response.output_text.done",
                "segment_id": "seg-1",
                "text": "hello",
            }
        )
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
        s.on_event({"type": "error", "error": {"code": "x", "message": "bad"}})
        self.assertIn("x", s.last_error)


if __name__ == "__main__":
    unittest.main()
