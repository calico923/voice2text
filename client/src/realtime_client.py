from __future__ import annotations

import asyncio
import base64
import inspect
import json
from typing import AsyncIterator

import websockets

DEFAULT_MODEL_ID = "mistralai/Voxtral-Mini-4B-Realtime-2602"


class RealtimeClient:
    def __init__(self, url: str, api_key: str = "", model: str = "") -> None:
        self.url = url
        self.api_key = api_key
        self.model = model
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
            "audio": base64.b64encode(pcm16_chunk).decode("ascii"),
        }
        await self._ws.send(json.dumps(payload, ensure_ascii=False))

    async def send_session_update(self, model: str | None = None) -> None:
        if self._ws is None:
            raise RuntimeError("not connected")
        await self._ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "model": model or self.model or DEFAULT_MODEL_ID,
                },
                ensure_ascii=False,
            )
        )

    async def send_commit(self, event_id: str = "commit-0001", final: bool = False) -> None:
        if self._ws is None:
            raise RuntimeError("not connected")
        await self._ws.send(json.dumps({"type": "input_audio_buffer.commit", "final": final}, ensure_ascii=False))

    async def send_response_create(self, event_id: str = "response-0001") -> None:
        raise RuntimeError("response.create is not supported by the current vLLM realtime server")

    async def recv_event(self, timeout_sec: float = 10.0) -> dict | None:
        if self._ws is None:
            raise RuntimeError("not connected")

        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            return None
        except websockets.ConnectionClosed:
            return {"type": "connection.closed"}

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"type": "invalid_json", "raw": raw}

    async def iter_events(self, timeout_sec: float = 10.0) -> AsyncIterator[dict]:
        while True:
            event = await self.recv_event(timeout_sec)
            if event is None or event.get("type") == "connection.closed":
                break
            yield event
