from __future__ import annotations

import math
import struct
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from audio_frame import normalize_to_pcm16_mono_16k, split_pcm16_into_chunks


class AudioFrameTest(unittest.TestCase):
    def test_split_pcm16_into_chunks_20ms(self) -> None:
        # 1 second of 16kHz mono PCM16 => 32000 bytes
        pcm16 = b"\x00\x00" * 16000
        chunks = split_pcm16_into_chunks(pcm16, 20)
        self.assertEqual(50, len(chunks))
        self.assertTrue(all(len(c) == 640 for c in chunks))

    def test_split_pcm16_into_chunks_40ms(self) -> None:
        pcm16 = b"\x00\x00" * 16000
        chunks = split_pcm16_into_chunks(pcm16, 40)
        self.assertEqual(25, len(chunks))
        self.assertTrue(all(len(c) == 1280 for c in chunks))

    def test_normalize_stereo_8k_to_16k_mono(self) -> None:
        sample_rate = 8000
        samples = sample_rate  # 1 sec
        raw = bytearray()
        for i in range(samples):
            val = int(32767 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
            raw.extend(struct.pack("<hh", val, val))  # stereo

        out = normalize_to_pcm16_mono_16k(bytes(raw), 2, 2, 8000)
        # ratecv has small rounding differences depending on implementation
        self.assertTrue(31990 <= len(out) <= 32010)


if __name__ == "__main__":
    unittest.main()
