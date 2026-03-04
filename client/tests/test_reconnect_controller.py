from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from reconnect_controller import ReconnectController


class ReconnectControllerTest(unittest.TestCase):
    def test_backoff_schedule(self) -> None:
        r = ReconnectController()
        self.assertEqual(1, r.next_delay_sec())
        self.assertEqual(2, r.next_delay_sec())
        self.assertEqual(4, r.next_delay_sec())
        self.assertEqual(8, r.next_delay_sec())
        self.assertEqual(10, r.next_delay_sec())
        self.assertEqual(10, r.next_delay_sec())

    def test_reset(self) -> None:
        r = ReconnectController()
        _ = [r.next_delay_sec() for _ in range(3)]
        r.reset()
        self.assertEqual(1, r.next_delay_sec())


if __name__ == "__main__":
    unittest.main()
