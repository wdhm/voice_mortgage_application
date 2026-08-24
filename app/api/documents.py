"""Document REST API: samples, preview, analyze, and human-review actions.

All routes go through the server-owned DocumentService; the browser never sees
raw analyzer payloads — only the sanitized extraction projection and the active
provider mode (so the demo is explicit about simulated vs real analysis).
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from ..documents.port import REQUIRED_FIELDS, UploadValidationError
from ..documents.samples import SAMPLE_KEYS, SAMPLES, render_payslip_html, sample_pdf_path
from ..documents.service import CONFIDENCE_THRESHOLD, validate_upload
from ..domain.models import DocumentState
from ..state import app_state

router = APIRouter(prefix="/api/documents")

# Contract identifier + version for the advisor's downloadable structured export.
# Bump the version if the shape changes so downstream consumers can adapt.
EXTRACTION_SCHEMA = "bankalfa.income-extraction"
EXTRACTION_SCHEMA_VERSION = "1.0"
_BANK_EXTRACTIONS_PATH = Path(__file__).resolve().parents[1] / "documents" / "extracted_payslips.json"


def _bank_extractions() -> dict:
    return json.loads(_BANK_EXTRACTIONS_PATH.read_text(encoding="utf-8"))


def _bank_payslips_with_live_emma() -> dict:
    payload = _bank_extractions()
    case = app_state.repo.get()
    emma = next(record for record in payload["payslips"] if record["id"] == "emma")
    accepted = case.accepted_income

    emma["customer"].update(
        {
            "name": case.customer_profile.display_name,
            "customer_number": case.customer_profile.customer_number,
            "city": case.customer_profile.city,
        }
    )
    if case.uploaded_document:
        emma["document"]["filename"] = case.uploaded_document.filename
        emma["document"]["content_type"] = case.uploaded_document.content_type
        emma["document"]["uploaded_at"] = case.uploaded_document.uploaded_at.isoformat()

    if accepted:
        emma["status"] = "accepted"
        emma["fields"] = {
            "employer_name": accepted.employer_name,
            "gross_salary_monthly": accepted.gross_salary_monthly,
            "net_salary_monthly": accepted.net_salary_monthly,
            "employment_type": accepted.employment_type,
            "pay_date": accepted.pay_date.isoformat(),
        }
        emma["confidence"] = {name: 1.0 for name in REQUIRED_FIELDS}
    elif case.document_state is DocumentState.review_required and case.extracted_income:
        emma["status"] = "review_required"
        emma["fields"] = {}
        emma["confidence"] = {}
        for name in REQUIRED_FIELDS:
            field = getattr(case.extracted_income, name)
            emma["fields"][name] = (
                field.normalized_value if field.normalized_value is not None else field.value
            )
            emma["confidence"][name] = field.confidence
    else:
        emma["status"] = "rejected"
        emma["fields"] = {name: None for name in REQUIRED_FIELDS}
        emma["confidence"] = {name: None for name in REQUIRED_FIELDS}
    return payload


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
        "rejection_reason": case.rejection_reason,
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


@router.get("/bank-extractions")
async def bank_extractions() -> dict:
    """Structured payslip output used by the bank's bulk-review workspace."""
    return _bank_payslips_with_live_emma()


@router.get("/bank-extractions/{record_id}/preview")
async def bank_extraction_preview(record_id: str) -> HTMLResponse:
    payload = _bank_payslips_with_live_emma()
    record = next((item for item in payload["payslips"] if item["id"] == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown payslip")
    if record_id == "emma" and record["status"] == "rejected":
        pdf = sample_pdf_path("low_confidence")
        if pdf is not None:
            return FileResponse(
                pdf,
                media_type="application/pdf",
                filename=pdf.name,
                content_disposition_type="inline",
            )

    fields = record["fields"]
    customer = record["customer"]
    gross = f"{fields['gross_salary_monthly']:,}".replace(",", " ")
    net = f"{fields['net_salary_monthly']:,}".replace(",", " ")
    themes = {
        "johan": {"accent": "#145b8c", "soft": "#eaf3f9", "layout": "sidebar", "font": "Arial"},
        "sara": {"accent": "#6c3a8f", "soft": "#f3ecf7", "layout": "boxed", "font": "Georgia"},
        "anders": {"accent": "#d5661f", "soft": "#fff2e8", "layout": "industrial", "font": "Verdana"},
        "linnea": {"accent": "#147d73", "soft": "#e8f5f3", "layout": "minimal", "font": "Tahoma"},
        "emma": {"accent": "#c9343a", "soft": "#f8ecec", "layout": "classic", "font": "Arial"},
    }
    theme = themes[record_id]
    html = f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><style>
body{{margin:0;background:#eceeed;font-family:{theme['font']},sans-serif;color:#172126}}
.sheet{{max-width:640px;margin:20px auto;background:#fff;padding:34px 40px;box-shadow:0 12px 30px #17212618;
  border-top:8px solid {theme['accent']}}}
.top{{display:flex;justify-content:space-between;border-bottom:2px solid {theme['accent']};padding-bottom:14px}}
.brand{{color:{theme['accent']};font-weight:700;font-size:20px}} .muted{{color:#5b6b6a;font-size:12px}}
.system{{display:inline-block;margin-bottom:8px;padding:5px 9px;background:{theme['soft']};color:{theme['accent']};
  border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}}
h1{{font-family:Georgia,serif;font-size:22px;margin:22px 0 4px}}
.row{{display:flex;justify-content:space-between;border-bottom:1px solid #d5dcda;padding:9px 0}}
.value{{font-weight:700}} .totals{{margin-top:22px;border-top:2px solid #172126}}
.net .value{{color:{theme['accent']}}}
.layout-sidebar .sheet{{padding-left:120px;position:relative;border-top:0;border-left:12px solid {theme['accent']}}}
.layout-sidebar .sheet:before{{content:"PAYROLL";position:absolute;left:18px;top:44px;color:{theme['accent']};
  font-size:11px;font-weight:700;letter-spacing:.18em;writing-mode:vertical-rl}}
.layout-boxed .sheet{{border:1px solid {theme['accent']};border-top:18px solid {theme['accent']};border-radius:12px}}
.layout-boxed .row{{margin:8px 0;padding:12px;border:1px solid #ded5e3;border-radius:8px;background:{theme['soft']}}}
.layout-boxed .totals{{border:0}}
.layout-industrial .sheet{{border:0;box-shadow:8px 8px 0 {theme['accent']};background:#fffdf9}}
.layout-industrial .top{{border-bottom:4px double {theme['accent']}}}
.layout-industrial h1{{font-family:Verdana,sans-serif;text-transform:uppercase;letter-spacing:.08em}}
.layout-minimal .sheet{{border-top:3px solid {theme['accent']};box-shadow:none}}
.layout-minimal .top{{border:0;padding-bottom:30px}}
.layout-minimal .row{{border:0;border-bottom:1px solid #edf1f0}}
</style></head><body><div class="sheet">
<div class="top"><div class="brand">{escape(str(fields['employer_name']))}<div class="muted">Arbetsgivare</div></div>
<div class="muted">Löneperiod: Augusti 2026<br>Utbetalningsdatum: {escape(str(fields['pay_date']))}</div></div>
<h1>Lönespecifikation</h1><p class="muted">{escape(customer['name'])} · {escape(customer['city'])}</p>
<div class="row"><span>Anställningsform</span><span class="value">{escape(str(fields['employment_type']))}</span></div>
<div class="totals"><div class="row"><span>Bruttolön</span><span class="value">{gross} kr</span></div>
<div class="row net"><span>Nettolön (utbetalas)</span><span class="value">{net} kr</span></div></div>
</div><script>document.body.className="layout-{theme['layout']}"</script></body></html>"""
    return HTMLResponse(html)


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
    app_state.remember_document(content, content_type)
    return _projection()


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:  # noqa: B008 (FastAPI dependency idiom)
    content = await file.read()
    try:
        validate_upload(content, file.content_type or "")
    except UploadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if app_state.documents.provider == "simulated":
        # Keep the OCR progress state visible long enough for the recorded demo.
        await asyncio.sleep(1.4)
    case = await app_state.documents.analyze(
        content=content, content_type=file.content_type or "", filename=file.filename or "upload", sample_key=None
    )
    if case.document_state is DocumentState.analysis_failed:
        raise HTTPException(
            status_code=502,
            detail="The payslip could not be analyzed. Check the document analysis provider and try again.",
        )
    app_state.remember_document(content, file.content_type)
    return _projection()


@router.delete("/upload")
async def remove_upload() -> dict:
    await app_state.documents.remove()
    app_state.forget_document()
    return _projection()


@router.get("/uploaded/preview")
async def uploaded_preview():
    """Stream the exact document the customer last submitted, for the advisor's
    source-document preview. Inline so the browser renders it in the iframe."""
    data = app_state.last_document_bytes
    if not data:
        raise HTTPException(status_code=404, detail="no uploaded document")
    return Response(
        content=data,
        media_type=app_state.last_document_content_type or "application/octet-stream",
        headers={"Content-Disposition": "inline"},
    )


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
