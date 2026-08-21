from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domain.models import DocumentStatus, ExtractedField
from app.domain.projections import service_projection
from app.domain.repository import repository
from app.realtime.events import add_event, broker
from app.tools.actions import PolicyError, accept_extracted_income

router = APIRouter(prefix="/api/service", tags=["service"])


class ReviewApproval(BaseModel):
    employer_name: str
    gross_salary_monthly: int
    net_salary_monthly: int
    employment_type: str
    pay_date: date
    notes: str | None = None


@router.get("/case")
async def get_service_case() -> dict[str, object]:
    return service_projection(repository.get())


@router.post("/documents/approve")
async def approve_document(request: ReviewApproval) -> dict[str, object]:
    case = repository.get()
    if case.document_status != DocumentStatus.REVIEW_REQUIRED or case.extracted_income is None:
        raise HTTPException(409, "No document is awaiting review")
    for name in ("employer_name", "gross_salary_monthly", "net_salary_monthly", "employment_type", "pay_date"):
        field: ExtractedField = getattr(case.extracted_income, name)
        field.original_value = field.value
        field.value = getattr(request, name)
        field.provenance = "human-approved"
    case.review_notes = request.notes
    case.document_status = DocumentStatus.ACCEPTED_AFTER_REVIEW
    try:
        accept_extracted_income(case, "human-approved")
    except PolicyError as error:
        raise HTTPException(409, str(error)) from error
    event = add_event(case, "document.approved", "Approve corrected payslip", "completed", "Bank employee")
    repository.save(case)
    await broker.publish(case, event)
    return service_projection(case)


@router.post("/documents/reject")
async def reject_document() -> dict[str, object]:
    case = repository.get()
    if case.document_status != DocumentStatus.REVIEW_REQUIRED:
        raise HTTPException(409, "No document is awaiting review")
    case.document_status = DocumentStatus.REJECTED_BY_REVIEWER
    case.accepted_income = None
    event = add_event(case, "document.rejected", "Reject payslip", "blocked", "Bank employee")
    repository.save(case)
    await broker.publish(case, event)
    return service_projection(case)


@router.post("/reset")
async def reset_demo() -> dict[str, object]:
    case = repository.reset()
    event = add_event(case, "case.reset", "Reset demo case", "completed", "Bank Alfa")
    repository.save(case)
    await broker.publish(case, event)
    return service_projection(case)
