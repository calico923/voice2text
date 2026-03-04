#!/usr/bin/env python3
"""Generate reusable 16kHz/mono/PCM16 wav for smoke test."""

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 16000
DURATION_SEC = 1.0
FREQ = 440.0
AMP = 0.25


def main() -> None:
    out = Path(__file__).resolve().parent / "test_ja_1s.wav"
    samples = int(SAMPLE_RATE * DURATION_SEC)

    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)

        frames = bytearray()
        for i in range(samples):
            t = i / SAMPLE_RATE
            val = AMP * math.sin(2.0 * math.pi * FREQ * t)
            pcm = int(max(-1.0, min(1.0, val)) * 32767)
            frames.extend(struct.pack("<h", pcm))
        wf.writeframes(frames)

    print(out)


if __name__ == "__main__":
    main()
