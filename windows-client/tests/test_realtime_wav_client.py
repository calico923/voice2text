from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import realtime_wav_client as client


def fake_which_factory(available: set[str]):
    def _fake_which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in available else None

    return _fake_which


class RealtimeWavClientTest(unittest.TestCase):
    def test_build_capture_command_prefers_override(self) -> None:
        command = client.build_capture_command(
            platform_name="win32",
            device="Mic Device",
            capture_cmd='custom-capture --device "{device}" --raw',
            which_fn=fake_which_factory(set()),
        )
        self.assertEqual(["custom-capture", "--device", "Mic Device", "--raw"], command)

    def test_build_capture_command_for_windows_uses_ffmpeg(self) -> None:
        command = client.build_capture_command(
            platform_name="win32",
            device="Microphone Array",
            which_fn=fake_which_factory({"ffmpeg"}),
        )
        self.assertEqual("ffmpeg", command[0])
        self.assertIn("dshow", command)
        self.assertIn("audio=Microphone Array", command)

    def test_build_capture_command_for_windows_requires_device(self) -> None:
        with self.assertRaises(ValueError):
            client.build_capture_command(
                platform_name="win32",
                which_fn=fake_which_factory({"ffmpeg"}),
            )

    def test_build_capture_command_for_linux_uses_arecord(self) -> None:
        command = client.build_capture_command(
            platform_name="linux",
            device="hw:2,0",
            which_fn=fake_which_factory({"arecord"}),
        )
        self.assertEqual("arecord", command[0])
        self.assertIn("-D", command)
        self.assertIn("hw:2,0", command)
        self.assertEqual("-", command[-1])

    def test_chunk_count_from_duration_rounds_up(self) -> None:
        self.assertEqual(3, client.chunk_count_from_duration(0.05, 20))
        self.assertEqual(125, client.chunk_count_from_duration(5.0, 40))

    def test_chunk_count_from_ms_rounds_up(self) -> None:
        self.assertEqual(30, client.chunk_count_from_ms(600, 20))
        self.assertEqual(20, client.chunk_count_from_ms(400, 20))
        self.assertEqual(0, client.chunk_count_from_ms(0, 20, allow_zero=True))

    def test_is_speech_chunk_uses_rms_threshold(self) -> None:
        silent = b"\x00\x00" * 320
        loud = b"\xff\x7f" * 320
        self.assertFalse(client.is_speech_chunk(silent, 100))
        self.assertTrue(client.is_speech_chunk(loud, 100))

    def test_should_commit_utterance_on_silence_or_max(self) -> None:
        self.assertTrue(
            client.should_commit_utterance(
                200,
                0,
                min_utterance_chunks=20,
                max_utterance_chunks=200,
                vad_silence_chunks=30,
            )
        )
        self.assertTrue(
            client.should_commit_utterance(
                40,
                30,
                min_utterance_chunks=20,
                max_utterance_chunks=200,
                vad_silence_chunks=30,
            )
        )
        self.assertFalse(
            client.should_commit_utterance(
                10,
                30,
                min_utterance_chunks=20,
                max_utterance_chunks=200,
                vad_silence_chunks=30,
            )
        )

    def test_classify_event(self) -> None:
        self.assertEqual("partial", client.classify_event("transcription.delta"))
        self.assertEqual("final", client.classify_event("transcription.done"))
        self.assertEqual("error", client.classify_event("error"))
        self.assertEqual("other", client.classify_event("session.created"))


if __name__ == "__main__":
    unittest.main()
