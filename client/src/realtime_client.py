from __future__ import annotations

import asyncio
import base64
import inspect
import json
from typing import AsyncIterator

import websockets


class RealtimeClient:
    def __init__(self, url: str, api_key: str = "") -> None:
        self.url = url
        self.api_key = api_key
        self._ws = None

    async def connect(self) -> None:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        connect_kwargs = {"max_size": 8_000_000}
        if headers:
            params = inspect.signature(websockets.connect).parameters
            if "additional_headers" in params:
                connect_kwargs["additional_headers"] = headers
            else:
                connect_kwargs["extra_headers"] = headers

        self._ws = await websockets.connect(self.url, **connect_kwargs)

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def send_append(self, pcm16_chunk: bytes, event_id: str) -> None:
        if self._ws is None:
            raise RuntimeError("not connected")
        payload = {
            "type": "input_audio_buffer.append",
            "event_id": event_id,
            "audio": base64.b64encode(pcm16_chunk).decode("ascii"),
        }
        await self._ws.send(json.dumps(payload, ensure_ascii=False))

    async def send_commit(self, event_id: str = "commit-0001") -> None:
        if self._ws is None:
            raise RuntimeError("not connected")
        await self._ws.send(
            json.dumps({"type": "input_audio_buffer.commit", "event_id": event_id}, ensure_ascii=False)
        )

    async def send_response_create(self, event_id: str = "response-0001") -> None:
        if self._ws is None:
            raise RuntimeError("not connected")
        await self._ws.send(
            json.dumps({"type": "response.create", "event_id": event_id}, ensure_ascii=False)
        )

    async def iter_events(self, timeout_sec: float = 10.0) -> AsyncIterator[dict]:
        if self._ws is None:
            raise RuntimeError("not connected")

        while True:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout_sec)
            except asyncio.TimeoutError:
                break
            except websockets.ConnectionClosed:
                break

            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                yield {"type": "invalid_json", "raw": raw}
