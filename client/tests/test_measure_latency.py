from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "tools"))

from measure_latency import percentile


class MeasureLatencyTest(unittest.TestCase):
    def test_percentile_empty(self) -> None:
        self.assertEqual(0.0, percentile([], 50))

    def test_percentile_values(self) -> None:
        values = [10, 20, 30, 40, 50]
        self.assertEqual(30.0, percentile(values, 50))
        self.assertEqual(50.0, percentile(values, 100))
        self.assertEqual(10.0, percentile(values, 0))


if __name__ == "__main__":
    unittest.main()
