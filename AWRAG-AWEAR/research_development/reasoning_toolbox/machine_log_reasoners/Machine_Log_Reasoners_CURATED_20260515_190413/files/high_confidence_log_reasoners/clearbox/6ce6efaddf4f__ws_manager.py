"""WebSocketManager — extracted from clearbox_bridge_server.py."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List

from fastapi import WebSocket, WebSocketDisconnect

LOGGER = logging.getLogger("clearbox_bridge_server")


class WebSocketManager:
    MAX_CONNECTIONS = 50  # Limit concurrent WebSocket connections

    def __init__(self):
        self.active: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        async with self._lock:
            if len(self.active) >= self.MAX_CONNECTIONS:
                await websocket.close(code=1013, reason="Too many connections")
                return False
        await websocket.accept()
        async with self._lock:
            self.active.append(websocket)
        return True

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message)
        async with self._lock:
            stale = []
            for ws in self.active:
                try:
                    await ws.send_text(payload)
                except (WebSocketDisconnect, Exception):
                    stale.append(ws)
            for ws in stale:
                if ws in self.active:
                    self.active.remove(ws)
