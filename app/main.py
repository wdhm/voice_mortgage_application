from __future__ import annotations

import logging
import os
from pathlib import Path

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

load_dotenv()

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor()

logger = logging.getLogger(__name__)

from app.api.customer import router as customer_router
from app.api.service import router as service_router
from app.domain.projections import customer_projection, service_projection
from app.domain.repository import repository
from app.realtime.events import broker
from app.voice.adapter import AzureVoiceLiveSession, VoiceConfigurationError

app = FastAPI(title="Bank Alfa Voice Mortgage Demo", version="0.1.0")
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    FastAPIInstrumentor.instrument_app(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(customer_router)
app.include_router(service_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    try:
        repository.get()
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(503, "In-memory repository is unavailable")
    return {"status": "ready"}


@app.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    session = AzureVoiceLiveSession(websocket)
    try:
        await session.run()
    except WebSocketDisconnect:
        pass
    except VoiceConfigurationError as error:
        await websocket.send_json({"type": "voice.error", "message": str(error)})
        await websocket.close(code=1011, reason="Voice Live is not configured")
    except Exception:
        logger.exception("Voice Live connection failed")
        await websocket.send_json(
            {"type": "voice.error", "message": "Voice Live could not start. Check Azure access and configuration."}
        )
        await websocket.close(code=1011, reason="Voice Live connection failed")


@app.websocket("/ws/{role}")
async def events_socket(websocket: WebSocket, role: str) -> None:
    if role not in {"customer", "service"}:
        await websocket.close(code=1008, reason="Unknown role")
        return
    await websocket.accept()
    case = repository.get()
    initial = customer_projection(case) if role == "customer" else service_projection(case)
    await websocket.send_json({"event_type": "case.snapshot", "case": initial})
    queue = broker.subscribe(role)
    try:
        while True:
            await websocket.send_json(await queue.get())
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(role, queue)


WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/")
    @app.get("/customer")
    @app.get("/customer/{path:path}")
    @app.get("/service")
    @app.get("/service/{path:path}")
    async def react_routes(path: str = "") -> FileResponse:
        del path
        return FileResponse(WEB_DIST / "index.html")
else:
    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse("/customer")
