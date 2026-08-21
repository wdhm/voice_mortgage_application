"""Document REST API: samples, preview, analyze, and human-review actions.

All routes go through the server-owned DocumentService; the browser never sees
raw analyzer payloads — only the sanitized extraction projection and the active
provider mode (so the demo is explicit about simulated vs real analysis).
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..documents.port import UploadValidationError
from ..documents.samples import SAMPLE_KEYS, SAMPLES, render_payslip_html
from ..documents.service import CONFIDENCE_THRESHOLD, validate_upload
from ..state import app_state

router = APIRouter(prefix="/api/documents")


def _projection() -> dict:
    """Sanitized view of the current document state for the UI."""
    case = app_state.repo.get()
    inc = case.extracted_income
    fields = None
    if inc is not None:
        fields = {}
        for name in ("employer_name", "gross_salary_monthly", "net_salary_monthly", "employment_type", "pay_date"):
            f = getattr(inc, name)
            passes = f.value is not None and f.confidence is not None and f.confidence >= CONFIDENCE_THRESHOLD
            fields[name] = {
                "value": f.value,
                "normalized_value": f.normalized_value,
                "confidence": f.confidence,
                "provenance": f.provenance.value,
                "source_grounding": f.source_grounding,
                "original_value": f.original_value,
                "passes": passes,
            }
    accepted = case.accepted_income.model_dump(mode="json") if case.accepted_income else None
    return {
        "document_state": case.document_state.value,
        "provider": app_state.documents.provider,
        "threshold": CONFIDENCE_THRESHOLD,
        "uploaded_document": case.uploaded_document.model_dump(mode="json") if case.uploaded_document else None,
        "fields": fields,
        "accepted_income": accepted,
        "review_record": case.review_record.model_dump(mode="json") if case.review_record else None,
    }


@router.get("/samples")
async def list_samples() -> list[dict]:
    return [{"key": s["key"], "label": s["label"], "description": s["description"]} for s in SAMPLES]


@router.get("/sample/{key}/preview", response_class=HTMLResponse)
async def sample_preview(key: str) -> HTMLResponse:
    if key not in SAMPLE_KEYS:
        raise HTTPException(status_code=404, detail="unknown sample")
    return HTMLResponse(render_payslip_html(key))


class AnalyzeSample(BaseModel):
    sample_key: str


@router.post("/analyze-sample")
async def analyze_sample(req: AnalyzeSample) -> dict:
    if req.sample_key not in SAMPLE_KEYS:
        raise HTTPException(status_code=404, detail="unknown sample")
    html = render_payslip_html(req.sample_key).encode("utf-8")
    filename = next(s["filename"] for s in SAMPLES if s["key"] == req.sample_key)
    await app_state.documents.analyze(
        content=html, content_type="text/html", filename=filename, sample_key=req.sample_key
    )
    return _projection()


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:  # noqa: B008 (FastAPI dependency idiom)
    content = await file.read()
    try:
        validate_upload(content, file.content_type or "")
    except UploadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await app_state.documents.analyze(
        content=content, content_type=file.content_type or "", filename=file.filename or "upload", sample_key=None
    )
    return _projection()


@router.get("/state")
async def get_state() -> dict:
    return _projection()


class ReviewEdit(BaseModel):
    field: str
    value: str


@router.post("/review/edit")
async def review_edit(req: ReviewEdit) -> dict:
    try:
        await app_state.documents.review_edit(req.field, req.value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _projection()


@router.post("/review/approve")
async def review_approve() -> dict:
    try:
        await app_state.documents.review_approve()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _projection()


@router.post("/review/reject")
async def review_reject() -> dict:
    await app_state.documents.review_reject()
    return _projection()
