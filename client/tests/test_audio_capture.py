from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from audio_capture import (
    build_capture_command,
    chunk_count_from_duration,
    chunk_count_from_ms,
    is_speech_chunk,
    should_commit_utterance,
)


def fake_which_factory(available: set[str]):
    def _fake_which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in available else None

    return _fake_which


class AudioCaptureTest(unittest.TestCase):
    def test_chunk_count_from_duration_rounds_up(self) -> None:
        self.assertEqual(3, chunk_count_from_duration(0.05, 20))
        self.assertEqual(125, chunk_count_from_duration(5.0, 40))

    def test_chunk_count_from_duration_rejects_non_positive(self) -> None:
        with self.assertRaises(ValueError):
            chunk_count_from_duration(0.0, 20)

    def test_chunk_count_from_ms_rounds_up(self) -> None:
        self.assertEqual(30, chunk_count_from_ms(600, 20))
        self.assertEqual(20, chunk_count_from_ms(400, 20))
        self.assertEqual(0, chunk_count_from_ms(0, 20, allow_zero=True))

    def test_is_speech_chunk_uses_rms_threshold(self) -> None:
        silent = b"\x00\x00" * 320
        loud = b"\xff\x7f" * 320
        self.assertFalse(is_speech_chunk(silent, 100))
        self.assertTrue(is_speech_chunk(loud, 100))

    def test_should_commit_utterance_on_silence_or_max(self) -> None:
        self.assertTrue(
            should_commit_utterance(
                200,
                0,
                min_utterance_chunks=20,
                max_utterance_chunks=200,
                vad_silence_chunks=30,
            )
        )
        self.assertTrue(
            should_commit_utterance(
                40,
                30,
                min_utterance_chunks=20,
                max_utterance_chunks=200,
                vad_silence_chunks=30,
            )
        )
        self.assertFalse(
            should_commit_utterance(
                10,
                30,
                min_utterance_chunks=20,
                max_utterance_chunks=200,
                vad_silence_chunks=30,
            )
        )

    def test_build_capture_command_prefers_env_override(self) -> None:
        command = build_capture_command(
            platform_name="darwin",
            device="2",
            env_command="custom-capture --device {device} --raw",
            which_fn=fake_which_factory(set()),
        )
        self.assertEqual(["custom-capture", "--device", "2", "--raw"], command)

    def test_build_capture_command_for_darwin_uses_ffmpeg(self) -> None:
        command = build_capture_command(
            platform_name="darwin",
            device="3",
            which_fn=fake_which_factory({"ffmpeg"}),
        )
        self.assertEqual("ffmpeg", command[0])
        self.assertIn("avfoundation", command)
        self.assertIn(":3", command)

    def test_build_capture_command_for_linux_uses_arecord(self) -> None:
        command = build_capture_command(
            platform_name="linux",
            device="hw:2,0",
            which_fn=fake_which_factory({"arecord"}),
        )
        self.assertEqual("arecord", command[0])
        self.assertIn("-D", command)
        self.assertIn("hw:2,0", command)
        self.assertEqual("-", command[-1])


if __name__ == "__main__":
    unittest.main()
