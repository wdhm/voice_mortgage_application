"""Debug/dev endpoints to drive tools and consent without the voice layer.

These exist so M2 is fully exercisable (and demo operators can smoke individual
steps) before M4 wires the same dispatcher to Voice Live function-calls. They are
mounted under /api/debug and are safe: they go through the exact same guarded
dispatcher and consent engine as production paths — no bypass.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..domain.fixtures import apply_accepted_income_emma
from ..domain.models import ConsentAction
from ..state import app_state

router = APIRouter(prefix="/api/debug")


class ToolCall(BaseModel):
    name: str
    args: dict = {}


@router.post("/tool")
async def run_tool(call: ToolCall) -> dict:
    outcome = await app_state.tools.dispatch(call.name, call.args)
    return {
        "ok": outcome.ok,
        "status": outcome.status.value,
        "summary": outcome.summary,
        "service": outcome.service,
        "idempotent_replay": outcome.idempotent_replay,
        "consent_consumed": outcome.consent_consumed,
        "result": outcome.result,
    }


class ConsentRequest(BaseModel):
    action: ConsentAction
    resource_scope: str | None = None


@router.post("/consent/request")
async def request_consent(req: ConsentRequest) -> dict:
    rec = await app_state.tools.request_consent(req.action, resource_scope=req.resource_scope)
    return {"consent_id": rec.consent_id, "status": rec.status.value, "action": rec.action.value}


class ConsentResolve(BaseModel):
    consent_id: str
    transcript: str | None = None


@router.post("/consent/resolve")
async def resolve_consent(req: ConsentResolve) -> dict:
    rec = await app_state.tools.resolve_consent(req.consent_id, req.transcript)
    return {"consent_id": rec.consent_id, "status": rec.status.value}


@router.post("/seed-income")
async def seed_income() -> dict:
    """Seed Emma's accepted income (stands in for the M3 document flow)."""
    case = app_state.repo.get()
    apply_accepted_income_emma(case)
    app_state.repo.set(case)
    return {"accepted_income": case.accepted_income.model_dump(mode="json")}
