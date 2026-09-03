import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Maps user_id to a list of active WebSockets
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_user(self, user_id: int, message_data: dict):
        """Send a JSON message to all active connections of a specific user."""
        if user_id in self.active_connections:
            message_text = json.dumps(message_data)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_text)
                except Exception:
                    # Ignore disconnected clients
                    pass


manager = ConnectionManager()
