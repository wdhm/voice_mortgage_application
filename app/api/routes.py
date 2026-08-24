"""REST API: health, case state, reset, and a temporary echo used for the M1 smoke test."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..domain.models import ConsentAction, ConsentStatus
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
        "tts_provider": settings.tts_provider,
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


class CreditReportApproval(BaseModel):
    approved: bool


@router.post("/mortgage/credit-report")
async def approve_and_fetch_credit_report(req: CreditReportApproval) -> dict:
    """Record explicit UI consent and run the guarded mock bureau check."""
    if not req.approved:
        raise HTTPException(status_code=400, detail="Explicit approval is required.")

    case = app_state.repo.get()
    if case.credit_result is not None:
        return {
            "status": "complete",
            "consent_status": "consumed",
            "credit_report": case.credit_result.model_dump(mode="json"),
        }

    pending = next(
        (
            record
            for record in reversed(case.consent_records)
            if record.action is ConsentAction.credit_check
            and record.status is ConsentStatus.requested
        ),
        None,
    )
    if pending is None:
        pending = await app_state.tools.request_consent(
            ConsentAction.credit_check,
            customer_id=case.customer_profile.customer_id,
        )

    consent = await app_state.tools.resolve_consent(
        pending.consent_id,
        "Yes, I approve the credit check.",
    )
    if consent.status is not ConsentStatus.granted:
        raise HTTPException(status_code=409, detail="Credit-check consent was not granted.")

    await app_state.voice.channel.publish(
        {
            "type": "consent",
            "status": consent.status.value,
            "action": "credit_check",
            "scope": None,
            "consent_id": consent.consent_id,
        }
    )
    outcome = await app_state.tools.dispatch(
        "run_credit_check",
        {
            "customerId": case.customer_profile.customer_id,
            "consent_id": consent.consent_id,
        },
    )
    if not outcome.ok:
        raise HTTPException(status_code=409, detail=outcome.summary)

    return {
        "status": "complete",
        "consent_status": "consumed",
        "credit_report": outcome.result,
    }


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
