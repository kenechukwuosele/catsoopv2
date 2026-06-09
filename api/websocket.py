import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from .auth import decode_token, SECRET

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    def join_room(self, websocket: WebSocket, room: str):
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
        token = websocket.query_params.get("token")
        if not token or not SECRET:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        try:
            from jwt import decode as _jwt_decode, InvalidTokenError, ExpiredSignatureError
            claims = _jwt_decode(token, SECRET, algorithms=["HS256"])
        except Exception as e:
            logger.info("WS auth rejected: %s", e)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        ws_username = str(claims.get("sub") or "")
        ws_is_admin = bool(claims.get("is_admin"))
        if not ws_username:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        room = "global"
        await manager.connect(websocket, room)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_text('{"error":"invalid json"}')
                    continue

                msg_type = msg.get("type", "")
                msg_room = msg.get("room", room)

                # All identity fields on outbound messages come from the verified
                # token, not from the client message — prevents impersonation.

                if msg_type == "JOIN":
                    manager.disconnect(websocket, room)
                    room = str(msg_room)
                    manager.join_room(websocket, room)
                    await manager.broadcast(room, json.dumps({
                        "type": "STUDENT_JOIN",
                        "username": ws_username,
                        "room": room,
                    }))

                elif msg_type == "LEAVE":
                    await manager.broadcast(room, json.dumps({
                        "type": "STUDENT_LEAVE",
                        "username": ws_username,
                        "room": room,
                    }))
                    manager.disconnect(websocket, room)
                    break

                elif msg_type == "SUBMISSION":
                    await manager.broadcast(room, json.dumps({
                        "type": "SUBMISSION",
                        "username": ws_username,
                        "score": msg.get("score"),
                        "question": msg.get("question"),
                        "room": room,
                    }))

                elif msg_type == "AFFECT_CHANGE":
                    await manager.broadcast(room, json.dumps({
                        "type": "AFFECT_CHANGE",
                        "username": ws_username,
                        "affect_state": msg.get("affect_state", "unknown"),
                        "room": room,
                    }))

                elif msg_type == "HINT_USED":
                    await manager.broadcast(room, json.dumps({
                        "type": "HINT_USED",
                        "username": ws_username,
                        "hint_level": msg.get("hint_level", 1),
                        "room": room,
                    }))

                elif msg_type == "PUSH_HINT":
                    if not ws_is_admin:
                        await websocket.send_text('{"error":"admin only"}')
                        continue
                    await manager.broadcast(room, json.dumps({
                        "type": "PUSH_HINT",
                        "target_username": msg.get("target_username"),
                        "hint_text": msg.get("hint_text", ""),
                        "room": room,
                    }))

                elif msg_type == "INSTRUCTOR_MESSAGE":
                    if not ws_is_admin:
                        await websocket.send_text('{"error":"admin only"}')
                        continue
                    await manager.broadcast(room, json.dumps({
                        "type": "INSTRUCTOR_MESSAGE",
                        "text": msg.get("text", ""),
                        "room": room,
                    }))

                elif msg_type == "QUIZ_DONE":
                    await manager.broadcast(room, json.dumps({
                        "type": "QUIZ_DONE",
                        "username": ws_username,
                        "room": room,
                        "timestamp": msg.get("timestamp", ""),
                    }))

                elif msg_type == "NEW_SUBMISSION":
                    await manager.broadcast(room, json.dumps({
                        "type": "NEW_SUBMISSION",
                        "student": ws_username,
                        "room": room,
                    }))

                else:
                    # Echo-back for unknown types is removed: it was a vector for
                    # echoing attacker-controlled payloads back into the room.
                    await websocket.send_text('{"error":"unknown message type"}')

        except WebSocketDisconnect:
            manager.disconnect(websocket, room)

    return router
