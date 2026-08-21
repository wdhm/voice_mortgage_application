"""Document REST API: samples, preview, analyze, and human-review actions.

All routes go through the server-owned DocumentService; the browser never sees
raw analyzer payloads — only the sanitized extraction projection and the active
provider mode (so the demo is explicit about simulated vs real analysis).
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from ..documents.port import REQUIRED_FIELDS, UploadValidationError
from ..documents.samples import SAMPLE_KEYS, SAMPLES, render_payslip_html, sample_pdf_path
from ..documents.service import CONFIDENCE_THRESHOLD, validate_upload
from ..state import app_state

router = APIRouter(prefix="/api/documents")

# Contract identifier + version for the advisor's downloadable structured export.
# Bump the version if the shape changes so downstream consumers can adapt.
EXTRACTION_SCHEMA = "bankalfa.income-extraction"
EXTRACTION_SCHEMA_VERSION = "1.0"


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


def _extraction_contract() -> dict | None:
    """Clean, reusable structured extraction contract for the advisor.

    Server-owned and sanitized (same shape as ``_projection`` fields, no raw
    analyzer payloads): the five normalized values with per-field confidence and
    provenance, plus analyzer/provider metadata. This is the artifact handed to a
    later step (e.g. the mortgage/voice conversation). Returns None when there is
    nothing to export yet.
    """
    case = app_state.repo.get()
    inc = case.extracted_income
    if inc is None:
        return None

    fields: dict[str, dict] = {}
    for name in REQUIRED_FIELDS:
        f = getattr(inc, name)
        passes = f.value is not None and f.confidence is not None and f.confidence >= CONFIDENCE_THRESHOLD
        fields[name] = {
            "value": f.value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence,
            "provenance": f.provenance.value,
            "source_grounding": f.source_grounding,
            "passes": passes,
        }

    doc = case.uploaded_document
    accepted = case.accepted_income.model_dump(mode="json") if case.accepted_income else None
    review = case.review_record.model_dump(mode="json") if case.review_record else None
    return {
        "schema": EXTRACTION_SCHEMA,
        "schema_version": EXTRACTION_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "case_id": case.case_id,
        "document_state": case.document_state.value,
        "document": (
            {
                "filename": doc.filename,
                "content_type": doc.content_type,
                "size_bytes": doc.size_bytes,
                "sample_key": doc.sample_key,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
            if doc
            else None
        ),
        "analyzer": {
            "provider": (doc.analyzer_provider if doc else None) or app_state.documents.provider,
            "analyzer_id": doc.analyzer_id if doc else None,
            "method": doc.analyzer_method if doc else None,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
        },
        "fields": fields,
        "accepted_income": accepted,
        "review": review,
    }


@router.get("/samples")
async def list_samples() -> list[dict]:
    return [{"key": s["key"], "label": s["label"], "description": s["description"]} for s in SAMPLES]


@router.get("/sample/{key}/preview")
async def sample_preview(key: str):
    if key not in SAMPLE_KEYS:
        raise HTTPException(status_code=404, detail="unknown sample")
    pdf = sample_pdf_path(key)
    if pdf is not None:
        # Real committed PDF: preview the actual application/pdf document inline
        # (inline disposition so the browser renders it in the iframe, not a download).
        return FileResponse(
            pdf,
            media_type="application/pdf",
            filename=pdf.name,
            content_disposition_type="inline",
        )
    return HTMLResponse(render_payslip_html(key))


class AnalyzeSample(BaseModel):
    sample_key: str


@router.post("/analyze-sample")
async def analyze_sample(req: AnalyzeSample) -> dict:
    if req.sample_key not in SAMPLE_KEYS:
        raise HTTPException(status_code=404, detail="unknown sample")
    filename = next(s["filename"] for s in SAMPLES if s["key"] == req.sample_key)
    pdf = sample_pdf_path(req.sample_key)
    if pdf is not None:
        content = pdf.read_bytes()
        content_type = "application/pdf"
    else:
        content = render_payslip_html(req.sample_key).encode("utf-8")
        content_type = "text/html"
    await app_state.documents.analyze(
        content=content, content_type=content_type, filename=filename, sample_key=req.sample_key
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


@router.get("/extraction.json")
async def extraction_json() -> JSONResponse:
    """Downloadable, pretty-printed structured extraction contract for the advisor."""
    contract = _extraction_contract()
    if contract is None:
        raise HTTPException(status_code=404, detail="no extraction available")
    return JSONResponse(
        content=contract,
        headers={"Content-Disposition": 'inline; filename="income-extraction.json"'},
    )


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
