from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from audio_capture import build_capture_command, chunk_count_from_duration


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
