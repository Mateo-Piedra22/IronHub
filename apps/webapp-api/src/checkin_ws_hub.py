from __future__ import annotations

import asyncio
from typing import Any, Dict, Set

from fastapi import WebSocket


class CheckinWsHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_sucursal: Dict[int, Set[WebSocket]] = {}

    async def connect(self, sucursal_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._by_sucursal.setdefault(int(sucursal_id), set()).add(websocket)

    async def disconnect(self, sucursal_id: int, websocket: WebSocket) -> None:
        sid = int(sucursal_id)
        async with self._lock:
            conns = self._by_sucursal.get(sid)
            if not conns:
                return
            conns.discard(websocket)
            if not conns:
                self._by_sucursal.pop(sid, None)

    async def broadcast(self, sucursal_id: int, message: Any) -> None:
        sid = int(sucursal_id)
        async with self._lock:
            targets = list(self._by_sucursal.get(sid) or [])

        if not targets:
            return

        async def _send_one(ws: WebSocket) -> None:
            try:
                await ws.send_json(message)
            except Exception:
                try:
                    await self.disconnect(sid, ws)
                finally:
                    try:
                        await ws.close()
                    except Exception:
                        pass

        await asyncio.gather(*(_send_one(ws) for ws in targets), return_exceptions=True)


checkin_ws_hub = CheckinWsHub()
