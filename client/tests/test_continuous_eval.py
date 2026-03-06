from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "tools"))

from continuous_eval import collect_event_metrics, parse_main_summary, summarize_vram_samples


class ContinuousEvalTest(unittest.TestCase):
    def test_parse_main_summary(self) -> None:
        stdout = "\n".join(
            [
                "partial: aaa",
                "summary: finals=1 partial_present=False error=-",
            ]
        )
        finals, partial_present, error = parse_main_summary(stdout)
        self.assertEqual(1, finals)
        self.assertFalse(partial_present)
        self.assertEqual("-", error)

    def test_collect_event_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events.jsonl"
            payloads = [
                {"event_type": "send_commit"},
                {"event_type": "final_text", "latency_ms": 510},
                {"event_type": "final_text", "latency_ms": 620},
                {"event_type": "error", "message": "x"},
            ]
            p.write_text("\n".join(json.dumps(v) for v in payloads), encoding="utf-8")
            m = collect_event_metrics(p)
            self.assertEqual(1, m["send_commit_count"])
            self.assertEqual(2, m["final_text_count"])
            self.assertEqual(1, m["error_event_count"])
            self.assertEqual([510, 620], m["latencies_ms"])

    def test_summarize_vram_samples(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "vram.jsonl"
            rows = [
                {"memory_used_mb": 8000, "memory_free_mb": 8000, "memory_total_mb": 16000},
                {"memory_used_mb": 9000, "memory_free_mb": 7000, "memory_total_mb": 16000},
            ]
            p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            out = summarize_vram_samples(p)
            self.assertTrue(out["available"])
            self.assertEqual(2, out["sample_count"])
            self.assertEqual(8000, out["memory_used_mb"]["min"])
            self.assertEqual(9000, out["memory_used_mb"]["max"])


if __name__ == "__main__":
    unittest.main()
