"""REST API: health, case state, reset, and a temporary echo used for the M1 smoke test."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings
from ..events.models import EventStatus
from ..state import app_state

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    """Readiness: reports config presence without leaking endpoints or secrets."""
    return {
        "status": "ok",
        "voice_provider": settings.voice_provider,
        "document_provider": settings.document_provider,
        "foundry_configured": bool(settings.foundry_endpoint),
        "epoch": app_state.repo.epoch,
    }


@router.get("/case")
async def get_case() -> dict:
    """Full current demo case (in-memory)."""
    return app_state.repo.get().model_dump(mode="json")


@router.get("/events")
async def get_events() -> list[dict]:
    """Current timeline history (sanitized events)."""
    return [e.model_dump(mode="json") for e in app_state.bus.history()]


@router.post("/reset")
async def reset() -> dict:
    """Reset the demo to canonical state (bumps epoch, clears timeline)."""
    await app_state.reset()
    return {"status": "reset", "epoch": app_state.repo.epoch}


class EchoRequest(BaseModel):
    label: str = "Echo"


@router.post("/echo")
async def echo(req: EchoRequest) -> dict:
    """M1 smoke helper: emit an event onto the timeline to prove the WebSocket path."""
    event = await app_state.bus.emit(
        event_type="demo.echo",
        label=req.label,
        status=EventStatus.completed,
        service="Demo",
    )
    return {"emitted": event.event_id, "sequence": event.sequence}
