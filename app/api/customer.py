from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.conversation.router import classify_customer_message, dispatch_intent
from app.documents.adapter import analyzer
from app.domain.models import DocumentStatus, IdentityStatus
from app.domain.projections import customer_projection
from app.domain.repository import repository
from app.realtime.events import add_event, broker
from app.tools.actions import PolicyError, accept_extracted_income

router = APIRouter(prefix="/api/customer", tags=["customer"])
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class DigitalDRequest(BaseModel):
    approved: bool


class MessageRequest(BaseModel):
    text: str


@router.get("/case")
async def get_customer_case() -> dict[str, object]:
    return customer_projection(repository.get())


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
) -> dict[str, object]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, "Use a PDF, PNG, or JPEG document")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(400, "The uploaded document is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The document must be 10 MB or smaller")
    case = repository.get()
    case.document_name = Path(file.filename or "payslip").name
    uploaded = add_event(case, "document.uploaded", "Upload payslip", "completed", "Bank Alfa")
    try:
        case.extracted_income = await analyzer.analyze(
            case.document_name,
            content,
            file.content_type or "application/octet-stream",
        )
    except Exception as error:
        case.document_status = DocumentStatus.ANALYSIS_FAILED
        case.accepted_income = None
        failed = add_event(
            case,
            "document.analysis_failed",
            "Analyze payslip",
            "blocked",
            "Azure Content Understanding",
        )
        repository.save(case)
        await broker.publish(case, uploaded)
        await broker.publish(case, failed)
        raise HTTPException(502, "Azure Content Understanding could not analyze this document") from error
    confidence_values = [
        field.get("confidence")
        for field in case.extracted_income.model_dump().values()
        if isinstance(field, dict)
    ]
    all_accepted = all(value is not None and value >= 0.85 for value in confidence_values)
    if all_accepted:
        case.document_status = DocumentStatus.ACCEPTED_AUTOMATICALLY
        accept_extracted_income(case, "automatically-verified")
        completed = add_event(
            case,
            "document.extracted",
            "Extract payslip",
            "completed",
            "Azure Content Understanding",
        )
    else:
        case.document_status = DocumentStatus.REVIEW_REQUIRED
        case.accepted_income = None
        completed = add_event(
            case,
            "document.review_required",
            "Review payslip extraction",
            "review",
            "Azure Content Understanding",
        )
    repository.save(case)
    await broker.publish(case, uploaded)
    await broker.publish(case, completed)
    return customer_projection(case)


@router.post("/digitald")
async def resolve_digitald(request: DigitalDRequest) -> dict[str, object]:
    case = repository.get()
    case.identity_status = IdentityStatus.IDENTIFIED if request.approved else IdentityStatus.DECLINED
    event = add_event(
        case,
        "identity.completed" if request.approved else "identity.declined",
        "DigitalD demo identification",
        "completed" if request.approved else "blocked",
        "DigitalD demo",
    )
    if request.approved:
        case.transcript.append(
            {"speaker": "assistant", "text": "Thanks, Emma. Your demo identity check is complete. How can I help?"}
        )
    repository.save(case)
    await broker.publish(case, event)
    return customer_projection(case)


@router.post("/messages")
async def send_message(request: MessageRequest) -> dict[str, object]:
    case = repository.get()
    text = request.text.strip()
    if not text:
        raise HTTPException(400, "Message cannot be empty")
    case.transcript.append({"speaker": "customer", "text": text})
    try:
        intent = await classify_customer_message(case, text)
        reply = dispatch_intent(case, intent, text)
    except PolicyError as error:
        repository.save(case)
        raise HTTPException(409, str(error)) from error
    case.transcript.append({"speaker": "assistant", "text": reply})
    event = add_event(case, "transcript.completed", "Conversation turn", "completed", "Microsoft Foundry")
    repository.save(case)
    await broker.publish(case, event)
    return {"reply": reply, "case": customer_projection(case)}
