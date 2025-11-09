# app/ws/manager.py
"""
Connection manager for multi-tenant WebSocket broadcasting.

Usage:
- In FastAPI route: await ws_manager.connect(...) / ws_manager.disconnect(...)
- From async code: await ws_manager.notify_clients(tenant_id, payload_dict)
- From sync code (e.g., pywa handlers): ws_manager.notify_clients_sync(tenant_id, payload_dict)
"""
from __future__ import annotations

import logging
import asyncio
import threading
from typing import Dict, Set, Optional

from fastapi import WebSocket

log = logging.getLogger("whatspy.ws")

class WebSocketConnectionManager:
    def __init__(self) -> None:
        # Map tenant_id -> set of WebSocket connections
        self.active: Dict[str, Set[WebSocket]] = {}

    async def connect(self, tenant_id: str, websocket: WebSocket) -> None:
        """Accept and register a websocket under a tenant."""
        await websocket.accept()
        if tenant_id not in self.active:
            self.active[tenant_id] = set()
        self.active[tenant_id].add(websocket)
        log.info("WS connected: tenant=%s total=%d", tenant_id, self.connection_count(tenant_id))

    def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        """Unregister a websocket from a tenant."""
        if tenant_id in self.active:
            conns = self.active[tenant_id]
            if websocket in conns:
                conns.discard(websocket)
            if not conns:
                # cleanup empty tenant bucket
                self.active.pop(tenant_id, None)
        log.info("WS disconnected: tenant=%s total=%d", tenant_id, self.connection_count(tenant_id))

    async def notify_clients(self, tenant_id: str, message_data: dict) -> None:
        """Async: send JSON to all connected clients of a tenant."""
        connections = list(self.active.get(tenant_id, set()))
        if not connections:
            return

        stale: Set[WebSocket] = set()
        for ws in connections:
            try:
                await ws.send_json(message_data)
            except Exception as e:
                # mark stale; we will remove after loop
                log.debug("WS send failed, marking stale: %s", e)
                stale.add(ws)

        # remove stale connections
        if stale:
            alive = self.active.get(tenant_id, set())
            for ws in stale:
                alive.discard(ws)
            if not alive:
                self.active.pop(tenant_id, None)

    # Convenience aliases
    async def broadcast(self, tenant_id: str, message_data: dict) -> None:
        await self.notify_clients(tenant_id, message_data)

    def connection_count(self, tenant_id: Optional[str] = None) -> int:
        if tenant_id is None:
            return sum(len(s) for s in self.active.values())
        return len(self.active.get(tenant_id, set()))

    def notify_clients_sync(self, tenant_id: str, message_data: dict) -> None:
        """
        Sync-safe helper to dispatch async notify from non-async contexts (e.g., pywa handlers).

        Strategy:
        - Try anyio.from_thread.run to hop into the running loop (works when called from worker thread)
        - Else, if we're on a running loop thread, create_task
        - Else, run the coroutine in a new daemon thread to avoid blocking
        """
        # Attempt best-case: anyio bridge
        try:
            import anyio
            try:
                anyio.from_thread.run(self.notify_clients, tenant_id, message_data)
                return
            except RuntimeError:
                # Not in a worker thread bound to an event loop; fallback below
                pass
        except Exception:
            # anyio not available or other issue; continue with fallbacks
            pass

        # If on a running loop (rare in sync funcs), schedule a task
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.notify_clients(tenant_id, message_data))
            return
        except RuntimeError:
            # No running loop in this thread
            pass

        # Last resort: run in a new thread with its own short-lived loop
        def _runner():
            try:
                asyncio.run(self.notify_clients(tenant_id, message_data))
            except Exception as e:
                log.debug("Background notify failed: %s", e)

        threading.Thread(target=_runner, daemon=True).start()


# Singleton manager instance
ws_manager = WebSocketConnectionManager()

# Public helpers
async def notify_clients(tenant_id: str, message_data: dict) -> None:
    await ws_manager.notify_clients(tenant_id, message_data)

def notify_clients_sync(tenant_id: str, message_data: dict) -> None:
    ws_manager.notify_clients_sync(tenant_id, message_data)