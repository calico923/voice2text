from __future__ import annotations

import asyncio
import math
import os
import shlex
import shutil
import sys
from dataclasses import dataclass, field
from typing import Callable

from audio_frame import pcm16_bytes_per_chunk


WhichFn = Callable[[str], str | None]


def chunk_count_from_duration(duration_sec: float, chunk_ms: int) -> int:
    if duration_sec <= 0:
        raise ValueError("duration_sec must be > 0")
    return max(1, math.ceil((duration_sec * 1000.0) / chunk_ms))


def build_capture_command(
    platform_name: str,
    device: str = "",
    env_command: str = "",
    which_fn: WhichFn = shutil.which,
) -> list[str]:
    configured_device = device or os.getenv("AUDIO_INPUT_DEVICE", "").strip()
    selected_device = configured_device or "0"

    if env_command:
        return shlex.split(env_command.format(device=selected_device))

    if platform_name == "darwin":
        if which_fn("ffmpeg"):
            return [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "avfoundation",
                "-i",
                f":{selected_device}",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "pipe:1",
            ]
        raise RuntimeError(
            "ffmpeg is required for macOS microphone capture, or set AUDIO_CAPTURE_CMD"
        )

    if platform_name.startswith("linux"):
        if which_fn("arecord"):
            command = [
                "arecord",
                "-q",
                "-f",
                "S16_LE",
                "-c",
                "1",
                "-r",
                "16000",
                "-t",
                "raw",
            ]
            if configured_device:
                command.extend(["-D", configured_device])
            command.append("-")
            return command
        raise RuntimeError(
            "arecord is required for Linux microphone capture, or set AUDIO_CAPTURE_CMD"
        )

    raise RuntimeError(
        f"unsupported microphone capture platform: {platform_name}. Set AUDIO_CAPTURE_CMD."
    )


@dataclass
class AudioCapture:
    chunk_ms: int
    device: str = ""
    env_command: str = ""
    platform_name: str = field(default_factory=lambda: sys.platform)
    which_fn: WhichFn = shutil.which
    _process: asyncio.subprocess.Process | None = field(default=None, init=False)
    _command: list[str] = field(default_factory=list, init=False)

    async def start(self) -> None:
        if self._process is not None:
            return

        self._command = build_capture_command(
            platform_name=self.platform_name,
            device=self.device,
            env_command=self.env_command or os.getenv("AUDIO_CAPTURE_CMD", "").strip(),
            which_fn=self.which_fn,
        )
        self._process = await asyncio.create_subprocess_exec(
            *self._command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def read_chunk(self) -> bytes | None:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("capture is not started")

        try:
            return await self._process.stdout.readexactly(pcm16_bytes_per_chunk(self.chunk_ms))
        except asyncio.IncompleteReadError as exc:
            return exc.partial or None

    async def iter_chunks(self, max_chunks: int | None = None):
        emitted = 0
        while max_chunks is None or emitted < max_chunks:
            chunk = await self.read_chunk()
            if not chunk:
                break
            emitted += 1
            yield chunk

    async def stop(self) -> None:
        if self._process is None:
            return

        process = self._process
        self._process = None

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    @property
    def command(self) -> list[str]:
        return list(self._command)
