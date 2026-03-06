#!/usr/bin/env python3
"""Minimal mock Realtime API server for local client validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass

import websockets


@dataclass
class SessionState:
    append_count: int = 0
    committed: bool = False
    session_updated: bool = False
    final_sent: bool = False


def build_error(code: str, message: str) -> str:
    return json.dumps(
        {
            "type": "error",
            "error": {
                "code": code,
                "message": message,
            },
        },
        ensure_ascii=False,
    )


async def handle_connection(websocket):
    state = SessionState()
    await websocket.send(
        json.dumps(
            {
                "type": "session.created",
                "id": "mock-session-1",
                "created": int(time.time()),
            },
            ensure_ascii=False,
        )
    )
    try:
        async for raw in websocket:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(build_error("invalid_json", "payload must be valid json"))
                continue

            event_type = event.get("type")
            if event_type == "session.update":
                state.session_updated = True
            elif event_type.startswith("input_audio_buffer.") and not state.session_updated:
                await websocket.send(
                    build_error(
                        "model_not_validated",
                        "send session.update before audio events",
                    )
                )
            elif event_type == "input_audio_buffer.append":
                state.append_count += 1
                if state.append_count in (1, 3, 5):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "transcription.delta",
                                "delta": f"delta-{state.append_count}",
                            },
                            ensure_ascii=False,
                        )
                    )
            elif event_type == "input_audio_buffer.commit":
                if event.get("final"):
                    if not state.committed:
                        await websocket.send(
                            build_error(
                                "missing_commit",
                                "commit is required before final=true",
                            )
                        )
                    elif not state.final_sent:
                        state.final_sent = True
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "transcription.done",
                                    "segment_id": "mock-seg-1",
                                    "text": "mock-final-text",
                                },
                                ensure_ascii=False,
                            )
                        )
                else:
                    state.committed = True
            elif event_type == "response.create":
                if state.committed and not state.final_sent:
                    state.final_sent = True
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "transcription.done",
                                "segment_id": "mock-seg-1",
                                "text": "mock-final-text",
                            },
                            ensure_ascii=False,
                        )
                    )
                else:
                    await websocket.send(build_error("missing_commit", "commit is required before response.create"))
            else:
                await websocket.send(build_error("unsupported_event", f"unsupported type: {event_type}"))
    except websockets.ConnectionClosed:
        return


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mock Realtime server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=18000)
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    async with websockets.serve(handle_connection, args.host, args.port):
        print(f"[mock] ws://{args.host}:{args.port}/v1/realtime")
        await asyncio.Future()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
