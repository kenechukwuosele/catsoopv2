from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.rooms:
            self.rooms[room] = [ws for ws in self.rooms[room] if ws != websocket]
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast(self, room: str, message: str):
        if room in self.rooms:
            for connection in self.rooms[room]:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass

    async def broadcast_all(self, message: str):
        for room in list(self.rooms.keys()):
            await self.broadcast(room, message)


manager = ConnectionManager()


def get_router() -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        room = "global"
        await manager.connect(websocket, room)
        try:
            while True:
                data = await websocket.receive_text()
                import json
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_text('{"error":"invalid json"}')
                    continue

                msg_type = msg.get("type", "")
                msg_room = msg.get("room", room)

                if msg_type == "JOIN":
                    manager.disconnect(websocket, room)
                    room = msg_room
                    await manager.connect(websocket, room)
                    await manager.broadcast(room, json.dumps({
                        "type": "STUDENT_JOIN",
                        "username": msg.get("username", "unknown"),
                        "room": room,
                    }))

                elif msg_type == "LEAVE":
                    await manager.broadcast(room, json.dumps({
                        "type": "STUDENT_LEAVE",
                        "username": msg.get("username", "unknown"),
                        "room": room,
                    }))
                    manager.disconnect(websocket, room)
                    break

                elif msg_type == "SUBMISSION":
                    await manager.broadcast(room, json.dumps({
                        "type": "SUBMISSION",
                        "username": msg.get("username", "unknown"),
                        "score": msg.get("score"),
                        "question": msg.get("question"),
                        "room": room,
                    }))

                elif msg_type == "AFFECT_CHANGE":
                    await manager.broadcast(room, json.dumps({
                        "type": "AFFECT_CHANGE",
                        "username": msg.get("username", "unknown"),
                        "affect_state": msg.get("affect_state", "unknown"),
                        "room": room,
                    }))

                elif msg_type == "HINT_USED":
                    await manager.broadcast(room, json.dumps({
                        "type": "HINT_USED",
                        "username": msg.get("username", "unknown"),
                        "hint_level": msg.get("hint_level", 1),
                        "room": room,
                    }))

                elif msg_type == "PUSH_HINT":
                    await manager.broadcast(room, json.dumps({
                        "type": "PUSH_HINT",
                        "target_username": msg.get("target_username"),
                        "hint_text": msg.get("hint_text", ""),
                        "room": room,
                    }))

                elif msg_type == "INSTRUCTOR_MESSAGE":
                    await manager.broadcast(room, json.dumps({
                        "type": "INSTRUCTOR_MESSAGE",
                        "text": msg.get("text", ""),
                        "room": room,
                    }))

                elif msg_type == "NEW_SUBMISSION":
                    await manager.broadcast(room, json.dumps({
                        "type": "NEW_SUBMISSION",
                        "student": msg.get("student", "unknown"),
                        "room": room,
                    }))

                else:
                    await websocket.send_text(f'{{"echo": {data}}}')

        except WebSocketDisconnect:
            manager.disconnect(websocket, room)

    return router
