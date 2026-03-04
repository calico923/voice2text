from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from paste_controller import PasteController


class FakeClock:
    def __init__(self) -> None:
        self.t = 100.0

    def now(self) -> float:
        return self.t

    def advance(self, sec: float) -> None:
        self.t += sec


class PasteControllerTest(unittest.TestCase):
    def test_empty_text_blocked(self) -> None:
        calls: list[tuple[list[str], str]] = []
        c = PasteController(enabled=True, runner=lambda cmd, s: calls.append((cmd, s)))
        ok, reason = c.paste("   ")
        self.assertFalse(ok)
        self.assertEqual("empty", reason)
        self.assertEqual([], calls)

    def test_duplicate_blocked(self) -> None:
        calls: list[tuple[list[str], str]] = []
        clock = FakeClock()
        c = PasteController(
            enabled=True,
            min_interval_ms=100,
            runner=lambda cmd, s: calls.append((cmd, s)),
            now_fn=clock.now,
        )
        ok1, _ = c.paste("hello")
        clock.advance(1.0)
        ok2, reason2 = c.paste("hello")
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertEqual("duplicate", reason2)
        self.assertEqual(2, len(calls))

    def test_rate_limit_blocked(self) -> None:
        calls: list[tuple[list[str], str]] = []
        clock = FakeClock()
        c = PasteController(
            enabled=True,
            min_interval_ms=700,
            runner=lambda cmd, s: calls.append((cmd, s)),
            now_fn=clock.now,
        )
        ok1, _ = c.paste("first")
        clock.advance(0.1)
        ok2, reason2 = c.paste("second")
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertEqual("rate_limited", reason2)
        self.assertEqual(2, len(calls))


if __name__ == "__main__":
    unittest.main()
