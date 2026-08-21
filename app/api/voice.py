"""Voice WebSocket: the browser's control + media channel for the conversation.

Outbound: sanitized voice messages (agent/user transcript, audio deltas, session /
consent / barge-in control) fanned out from the VoiceOrchestrator's
channel. Inbound: presenter + customer control frames routed to the orchestrator.

The orchestrator (not the browser) owns all governance — this route only shuttles
frames.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..state import app_state

router = APIRouter()


@router.websocket("/ws/voice")
async def voice_ws(ws: WebSocket) -> None:
    await ws.accept()
    orch = app_state.voice
    queue = orch.channel.subscribe()
    try:
        await ws.send_json({"type": "hello", "provider": orch.provider, "epoch": app_state.repo.epoch})

        async def _pump() -> None:
            while True:
                message = await queue.get()
                await ws.send_json(message)

        pump = asyncio.create_task(_pump())
        try:
            while True:
                frame = await ws.receive_json()
                await _handle_inbound(orch, frame)
        finally:
            pump.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        orch.channel.unsubscribe(queue)


async def _handle_inbound(orch, frame: dict) -> None:
    kind = frame.get("type")
    if kind == "start":
        await orch.start()
    elif kind == "text":
        await orch.user_text(frame.get("text", ""))
    elif kind == "audio":
        await orch.user_audio(frame.get("pcm", ""))
    elif kind == "audio_commit":
        await orch.user_audio_commit()
    elif kind == "barge_in":
        await orch.barge_in()
    elif kind == "stop":
        await orch.stop()


@router.post("/api/voice/start")
async def voice_start() -> dict:
    if not await app_state.voice.start():
        raise HTTPException(status_code=503, detail="Unable to start the configured voice provider.")
    return {"status": "started", "provider": app_state.voice.provider}


@router.post("/api/voice/stop")
async def voice_stop() -> dict:
    await app_state.voice.stop()
    return {"status": "stopped"}
