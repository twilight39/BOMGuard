"""WebSocket manager for real-time updates."""

from fastapi import WebSocket


class WebSocketManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        for connection in self._connections:
            await connection.send_json(message)


ws_manager = WebSocketManager()
