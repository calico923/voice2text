from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable


Runner = Callable[[list[str], str], None]
NowFn = Callable[[], float]


def _default_runner(cmd: list[str], stdin_text: str) -> None:
    subprocess.run(cmd, input=stdin_text, text=True, check=True)


@dataclass
class PasteController:
    enabled: bool
    min_interval_ms: int = 700
    runner: Runner = _default_runner
    now_fn: NowFn = time.monotonic
    _last_paste_at: float = field(default=0.0, init=False)
    _last_text: str = field(default="", init=False)

    def should_paste(self, text: str) -> tuple[bool, str]:
        normalized = text.strip()
        if not self.enabled:
            return False, "disabled"
        if not normalized:
            return False, "empty"
        if normalized == self._last_text:
            return False, "duplicate"
        elapsed_ms = (self.now_fn() - self._last_paste_at) * 1000.0
        if self._last_paste_at > 0 and elapsed_ms < self.min_interval_ms:
            return False, "rate_limited"
        return True, "ok"

    def paste(self, text: str) -> tuple[bool, str]:
        ok, reason = self.should_paste(text)
        if not ok:
            return ok, reason

        normalized = text.strip()
        self.runner(["pbcopy"], normalized)
        self.runner(
            [
                "osascript",
                "-e",
                'tell application "System Events" to keystroke "v" using command down',
            ],
            "",
        )
        self._last_paste_at = self.now_fn()
        self._last_text = normalized
        return True, "ok"
