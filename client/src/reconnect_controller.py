from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReconnectController:
    schedule_sec: list[int] = field(default_factory=lambda: [1, 2, 4, 8, 10])
    _attempt: int = 0

    def next_delay_sec(self) -> int:
        idx = min(self._attempt, len(self.schedule_sec) - 1)
        delay = self.schedule_sec[idx]
        self._attempt += 1
        return delay

    def reset(self) -> None:
        self._attempt = 0
