"""WebSocket manager for real-time updates."""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        self._loop = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        disconnected: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    def broadcast_sync(self, message: dict[str, Any]) -> None:
        """Fire-and-forget broadcast from synchronous code.

        Tries to schedule on the running event loop (e.g. inside FastAPI).
        If called from a different thread than the one that accepted the
        WebSocket connections, falls back to the captured event loop so tests
        and mixed sync/async callers still deliver the message.
        Silently ignores if no loop is available (e.g. plain Celery worker).
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
            return
        except RuntimeError:
            pass

        loop = self._loop
        if loop is not None and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
        else:
            logger.debug("No event loop available for WebSocket broadcast")


ws_manager = WebSocketManager()
