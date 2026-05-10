"""
WebSocket connection manager — broadcasts live call events to all connected dashboard clients.
"""
import json
from typing import Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, event_type: str, data: dict):
        """Send an event to all connected clients."""
        message = json.dumps({"event": event_type, "data": data})
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Singleton manager used across the application
manager = ConnectionManager()
