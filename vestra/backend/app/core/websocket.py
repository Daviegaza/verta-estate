"""
WebSocket Manager — real-time push for notifications, messages, and payment status.

Architecture:
  - ConnectionManager maintains an in-memory user_id -> set[WebSocket] mapping.
  - Online presence is stored in Redis with a TTL (60s), renewed by heartbeat pings.
  - Services import the singleton `manager` and call broadcast_to_user() to push events.
  - The handle_ws() coroutine is the FastAPI WebSocket endpoint handler.
"""
from __future__ import annotations

import contextlib
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.core.redis import get_redis

logger = logging.getLogger("vestra")

# Redis key prefix and TTL for online presence
ONLINE_PREFIX = "vestra:online:"
ONLINE_TTL = 60  # seconds; heartbeat pings renew this


class ConnectionManager:
    """
    Manages WebSocket connections per user.

    In-memory mapping: user_id -> set[WebSocket]
    Redis-backed online presence with TTL heartbeats.
    """

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}

    # ── Connection lifecycle ─────────────────────────────────────────────────

    async def connect(self, ws: WebSocket, user_id: int) -> None:
        """Accept a WebSocket and register the user."""
        await ws.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(ws)

        await self._set_online(user_id, True)

        logger.info(
            '{"event":"ws_connect","user_id":%d,"connections":%d}',
            user_id,
            len(self._connections[user_id]),
        )

    async def disconnect(self, ws: WebSocket, user_id: int) -> None:
        """Remove a WebSocket connection and clear online status if last."""
        if user_id in self._connections:
            self._connections[user_id].discard(ws)
            if not self._connections[user_id]:
                del self._connections[user_id]
                await self._set_online(user_id, False)

        logger.info('{"event":"ws_disconnect","user_id":%d}', user_id)

    # ── Broadcasting ─────────────────────────────────────────────────────────

    async def broadcast_to_user(self, user_id: int, message: dict) -> None:
        """
        Send a JSON message to every WebSocket connection belonging to a user.

        Dead connections are pruned silently.
        """
        ws_set = self._connections.get(user_id)
        if not ws_set:
            return

        dead: set[WebSocket] = set()
        payload = json.dumps(message, default=str)

        for ws in ws_set:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        if dead:
            self._connections[user_id] -= dead
            if not self._connections[user_id]:
                del self._connections[user_id]
                await self._set_online(user_id, False)

    async def broadcast_to_channel(self, channel: str, message: dict) -> None:
        """Broadcast to a named channel (reserved for future multi-tenant use)."""
        # Not implemented yet — would use Redis pub/sub for horizontal scaling.
        pass

    # ── Typing indicators ────────────────────────────────────────────────────

    async def send_typing_indicator(
        self, sender_id: int, receiver_id: int, is_typing: bool
    ) -> None:
        """Send a typing indicator to the receiving user."""
        await self.broadcast_to_user(
            receiver_id,
            {
                "type": "typing",
                "payload": {"sender_id": sender_id, "is_typing": is_typing},
            },
        )

    # ── Online presence (Redis-backed) ───────────────────────────────────────

    async def _set_online(self, user_id: int, is_online: bool) -> None:
        """Set or clear online status in Redis."""
        r = await get_redis()
        if r is None:
            return
        key = f"{ONLINE_PREFIX}{user_id}"
        try:
            if is_online:
                await r.setex(key, ONLINE_TTL, "1")
            else:
                await r.delete(key)
        except Exception:
            pass

    async def renew_online_status(self, user_id: int) -> None:
        """Renew the online TTL (called on each heartbeat ping)."""
        r = await get_redis()
        if r is None:
            return
        with contextlib.suppress(Exception):
            await r.expire(f"{ONLINE_PREFIX}{user_id}", ONLINE_TTL)

    async def is_user_online(self, user_id: int) -> bool:
        """Check if a user is currently online."""
        r = await get_redis()
        if r is None:
            return False
        try:
            return bool(await r.exists(f"{ONLINE_PREFIX}{user_id}"))
        except Exception:
            return False

    async def get_online_users(self, user_ids: list[int]) -> dict[int, bool]:
        """Batch-check online status for a list of user IDs."""
        r = await get_redis()
        if r is None:
            return dict.fromkeys(user_ids, False)
        try:
            pipe = r.pipeline()
            for uid in user_ids:
                pipe.exists(f"{ONLINE_PREFIX}{uid}")
            results = await pipe.execute()
            return dict(zip(user_ids, (bool(x) for x in results), strict=False))
        except Exception:
            return dict.fromkeys(user_ids, False)

    # ── Query helpers ───────────────────────────────────────────────────────

    @property
    def active_connections(self) -> int:
        """Total active WebSocket connections across all users."""
        return sum(len(ws_set) for ws_set in self._connections.values())

    @property
    def online_user_count(self) -> int:
        """Number of distinct users with active connections."""
        return len(self._connections)


# Singleton — import this from services to push events
manager = ConnectionManager()


# ── WebSocket endpoint handler ────────────────────────────────────────────────


async def handle_ws(websocket: WebSocket) -> None:
    """
    WebSocket endpoint handler.

    Accepts a ``token`` query parameter containing a valid JWT access token.
    Once connected, the client and server exchange JSON messages:

    **Client -> Server:**
        ``{"type": "ping"}``
            Heartbeat — server replies with ``{"type": "pong"}`` and renews the
            online TTL.

        ``{"type": "typing", "payload": {"receiver_id": <int>, "is_typing": <bool>}}``
            Notify the receiver that the sender is typing / stopped typing.

        ``{"type": "online_status", "payload": {"user_ids": [<int>, ...]}}``
            Request batch online status. Server replies with
            ``{"type": "online_status_batch", "payload": {<user_id>: <bool>, ...}}``.

    **Server -> Client:**
        ``{"type": "notification", "payload": {...}}``
            Pushed by notification_service.

        ``{"type": "message", "payload": {...}}``
            Pushed by messaging_service when a new message arrives.

        ``{"type": "payment_status", "payload": {...}}``
            Pushed by payment_service when payment status changes.

        ``{"type": "typing", "payload": {"sender_id": <int>, "is_typing": <bool>}}``
            Relay of a typing indicator from another user.

        ``{"type": "online_status_batch", "payload": {<user_id>: <bool>, ...}}``
            Response to a batch online-status request.

        ``{"type": "pong"}``
            Heartbeat reply.
    """
    from app.core.security import decode_token

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = decode_token(token)
        user_id: int = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                await manager.renew_online_status(user_id)

            elif msg_type == "typing":
                payload_data = data.get("payload", {})
                receiver_id = payload_data.get("receiver_id")
                is_typing = payload_data.get("is_typing", False)
                if receiver_id:
                    await manager.send_typing_indicator(
                        user_id, int(receiver_id), bool(is_typing)
                    )

            elif msg_type == "online_status":
                user_ids = data.get("payload", {}).get("user_ids", [])
                if user_ids:
                    statuses = await manager.get_online_users(
                        [int(uid) for uid in user_ids]
                    )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "online_status_batch",
                                "payload": statuses,
                            }
                        )
                    )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(
            '{"event":"ws_error","user_id":%d,"error":"%s"}',
            user_id,
            str(e)[:200],
            exc_info=True,
        )
    finally:
        await manager.disconnect(websocket, user_id)
