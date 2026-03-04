from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from logger import JsonlLogger


class LoggerTest(unittest.TestCase):
    def test_write_jsonl_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events.jsonl"
            log = JsonlLogger(enabled=True, path=str(p))
            log.log("test", x=1)
            line = p.read_text(encoding="utf-8").strip()
            payload = json.loads(line)
            self.assertEqual("test", payload["event_type"])
            self.assertEqual(1, payload["x"])

    def test_no_file_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events.jsonl"
            log = JsonlLogger(enabled=False, path=str(p))
            log.log("test")
            self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()
