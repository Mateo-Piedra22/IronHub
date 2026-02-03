from __future__ import annotations

import asyncio
from typing import Any, Optional, Set

from fastapi import WebSocket


class CheckinWsHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_room: dict[str, Set[WebSocket]] = {}

    def _room_key(self, sucursal_id: int, tenant: Optional[str]) -> str:
        t = ""
        if tenant is None:
            try:
                from src.database.tenant_connection import get_current_tenant

                t = str(get_current_tenant() or "").strip().lower()
            except Exception:
                t = ""
        else:
            t = str(tenant or "").strip().lower()
        return f"{t}|{int(sucursal_id)}"

    async def connect(self, sucursal_id: int, websocket: WebSocket, tenant: Optional[str] = None) -> None:
        await websocket.accept()
        rk = self._room_key(int(sucursal_id), tenant)
        async with self._lock:
            self._by_room.setdefault(rk, set()).add(websocket)

    async def disconnect(self, sucursal_id: int, websocket: WebSocket, tenant: Optional[str] = None) -> None:
        rk = self._room_key(int(sucursal_id), tenant)
        async with self._lock:
            conns = self._by_room.get(rk)
            if not conns:
                return
            conns.discard(websocket)
            if not conns:
                self._by_room.pop(rk, None)

    async def broadcast(self, sucursal_id: int, message: Any, tenant: Optional[str] = None) -> None:
        rk = self._room_key(int(sucursal_id), tenant)
        async with self._lock:
            targets = list(self._by_room.get(rk) or [])

        if not targets:
            return

        async def _send_one(ws: WebSocket) -> None:
            try:
                await ws.send_json(message)
            except Exception:
                try:
                    await self.disconnect(int(sucursal_id), ws, tenant=tenant)
                finally:
                    try:
                        await ws.close()
                    except Exception:
                        pass

        await asyncio.gather(*(_send_one(ws) for ws in targets), return_exceptions=True)


checkin_ws_hub = CheckinWsHub()
