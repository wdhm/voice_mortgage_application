"""Application WebSocket: streams sanitized timeline events to the browser.

On connect, replays current history (so a late client sees the full timeline),
then forwards live events. In M4 this same socket also carries audio frames and
transcript events.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..state import app_state

router = APIRouter()


@router.websocket("/ws/events")
async def events_ws(ws: WebSocket) -> None:
    await ws.accept()
    queue = app_state.bus.subscribe()
    try:
        # Replay history so a freshly connected client is in sync.
        for event in app_state.bus.history():
            await ws.send_json({"kind": "event", "data": event.model_dump(mode="json")})
        await ws.send_json({"kind": "ready", "epoch": app_state.repo.epoch})

        async def _pump() -> None:
            while True:
                event = await queue.get()
                await ws.send_json({"kind": "event", "data": event.model_dump(mode="json")})

        pump = asyncio.create_task(_pump())
        try:
            # Keep the socket alive; ignore any inbound control messages for now.
            while True:
                await ws.receive_text()
        finally:
            pump.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        app_state.bus.unsubscribe(queue)
