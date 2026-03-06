from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TranscriptStore:
    partial: str = ""
    finals: list[str] = field(default_factory=list)
    seen_segment_ids: set[str] = field(default_factory=set)
    last_error: str = ""

    def on_event(self, event: dict) -> None:
        event_type = event.get("type", "")
        if event_type == "transcription.delta":
            self.partial += str(event.get("delta", ""))
            return

        if event_type == "response.output_text.delta":
            self.partial = str(event.get("delta", ""))
            return

        if event_type in {"transcription.done", "response.output_text.done"}:
            segment_id = str(event.get("segment_id", ""))
            text = str(event.get("text", "")).strip()
            if not text:
                self.partial = ""
                return
            if segment_id and segment_id in self.seen_segment_ids:
                self.partial = ""
                return
            if segment_id:
                self.seen_segment_ids.add(segment_id)
            self.finals.append(text)
            self.partial = ""
            return

        if event_type == "error":
            err = event.get("error", {})
            if isinstance(err, dict):
                code = str(err.get("code", "unknown"))
                msg = str(err.get("message", ""))
            else:
                code = str(event.get("code", "unknown"))
                msg = str(err)
            self.last_error = f"{code}: {msg}".strip()
