#!/usr/bin/env python3
"""Minimal mock Realtime API server for local client validation."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass

import websockets


@dataclass
class SessionState:
    append_count: int = 0
    committed: bool = False


async def handle_connection(websocket):
    state = SessionState()
    try:
        async for raw in websocket:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "error": {
                                "code": "invalid_json",
                                "message": "payload must be valid json",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            event_type = event.get("type")
            if event_type == "input_audio_buffer.append":
                state.append_count += 1
                if state.append_count in (1, 3, 5):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "response.output_text.delta",
                                "response_id": "mock-resp-1",
                                "segment_id": "mock-seg-1",
                                "delta": f"delta-{state.append_count}",
                            },
                            ensure_ascii=False,
                        )
                    )
            elif event_type == "input_audio_buffer.commit":
                state.committed = True
            elif event_type == "response.create":
                if state.committed:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "response.output_text.done",
                                "response_id": "mock-resp-1",
                                "segment_id": "mock-seg-1",
                                "text": "mock-final-text",
                            },
                            ensure_ascii=False,
                        )
                    )
                else:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "error": {
                                    "code": "missing_commit",
                                    "message": "commit is required before response.create",
                                },
                            },
                            ensure_ascii=False,
                        )
                    )
            else:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "error": {
                                "code": "unsupported_event",
                                "message": f"unsupported type: {event_type}",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
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
