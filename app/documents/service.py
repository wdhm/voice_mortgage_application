"""Document service: turns an AnalyzerResult into case state under the confidence
policy, and owns the human-review actions. Server-owned like every other mutation.

Confidence policy (docs/functional-specification.md):
  * straight-through acceptance requires every required field present with
    confidence >= 0.85 (missing confidence counts as low);
  * otherwise the whole extraction is review_required;
  * nothing reaches accepted_income before auto-acceptance or reviewer approval;
  * reviewer edits keep the original value and set provenance to human-approved.
"""
from __future__ import annotations

import asyncio
import re
from datetime import UTC, date, datetime

from ..domain.models import (
    AcceptedIncome,
    CaseOutcome,
    DemoCase,
    DocumentState,
    ExtractedIncome,
    IncomeField,
    Provenance,
    ReviewRecord,
    UploadedDocument,
)
from ..domain.repository import CaseRepository
from ..events.bus import EventBus
from ..events.models import EventStatus
from .port import (
    ACCEPTED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    REQUIRED_FIELDS,
    AnalysisError,
    AnalyzerResult,
    DocumentAnalyzer,
    UploadValidationError,
)

CONFIDENCE_THRESHOLD = 0.85


def _now() -> datetime:
    return datetime.now(UTC)


def validate_upload(content: bytes, content_type: str) -> None:
    if not content:
        raise UploadValidationError("The file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadValidationError("The file is larger than the 10 MB limit.")
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise UploadValidationError(
            f"Unsupported type '{content_type}'. Upload a PDF or an image (PNG, JPEG, WEBP, TIFF)."
        )


def _field_ok(f: IncomeField) -> bool:
    return f.value is not None and f.confidence is not None and f.confidence >= CONFIDENCE_THRESHOLD


def _parse_amount(raw) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return round(raw)
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


def _parse_date(raw) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _to_income(result: AnalyzerResult) -> ExtractedIncome:
    def mk(name: str) -> IncomeField:
        fx = result.fields.get(name)
        if fx is None:
            return IncomeField(name=name, provenance=Provenance.extracted)
        return IncomeField(
            name=name,
            value=fx.value,
            normalized_value=fx.normalized_value,
            confidence=fx.confidence,
            source_grounding=fx.source_grounding,
            provenance=Provenance.extracted,
        )

    return ExtractedIncome(
        employer_name=mk("employer_name"),
        gross_salary_monthly=mk("gross_salary_monthly"),
        net_salary_monthly=mk("net_salary_monthly"),
        employment_type=mk("employment_type"),
        pay_date=mk("pay_date"),
    )


def _fields(inc: ExtractedIncome) -> dict[str, IncomeField]:
    return {name: getattr(inc, name) for name in REQUIRED_FIELDS}


class DocumentService:
    def __init__(self, repo: CaseRepository, bus: EventBus, analyzer: DocumentAnalyzer) -> None:
        self._repo = repo
        self._bus = bus
        self._analyzer = analyzer
        self._lock = asyncio.Lock()

    @property
    def provider(self) -> str:
        return self._analyzer.provider

    # ------------------------------------------------------------------ #
    async def analyze(
        self, *, content: bytes, content_type: str, filename: str, sample_key: str | None = None
    ) -> DemoCase:
        epoch_before = self._repo.epoch
        await self._bus.emit(
            event_type="document.analyzing",
            label="Analyze payslip",
            status=EventStatus.running,
            service="Document analysis",
        )
        try:
            result = await self._analyzer.analyze(
                content=content, content_type=content_type, filename=filename, sample_key=sample_key
            )
        except AnalysisError as exc:
            async with self._lock:
                if self._repo.epoch != epoch_before:
                    return self._repo.get()
                case = self._repo.get()
                case.document_state = DocumentState.analysis_failed
                self._repo.set(case)
            await self._bus.emit(
                event_type="document.failed", label=f"Analysis failed: {exc}",
                status=EventStatus.failed, service="Document analysis",
            )
            return self._repo.get()

        async with self._lock:
            # Epoch guard: a reset during analysis wins; discard stale result.
            if self._repo.epoch != epoch_before:
                return self._repo.get()
            case = self._repo.get()
            case.uploaded_document = UploadedDocument(
                filename=filename,
                content_type=content_type,
                size_bytes=len(content),
                sample_key=sample_key,
                uploaded_at=_now(),
                analyzer_provider=result.provider,
                analyzer_id=result.analyzer_id,
                analyzer_method=result.method,
            )
            extracted = _to_income(result)
            case.extracted_income = extracted
            case.review_record = None
            case.accepted_income = None

            failing = [n for n, f in _fields(extracted).items() if not _field_ok(f)]
            if not failing:
                case.accepted_income = _build_accepted(extracted, Provenance.extracted)
                case.document_state = DocumentState.accepted_automatically
            else:
                case.document_state = DocumentState.review_required
            self._repo.set(case)

        if not failing:
            await self._bus.emit(
                event_type="document.accepted", label="Income extracted and accepted",
                status=EventStatus.completed, service="Document analysis",
            )
        else:
            await self._bus.emit(
                event_type="document.review_required",
                label=f"Human review required ({len(failing)} field(s) below {int(CONFIDENCE_THRESHOLD*100)}%)",
                status=EventStatus.review, service="Document analysis",
            )
        return self._repo.get()

    # ------------------------------------------------------------------ #
    async def review_edit(self, field_name: str, new_value: str) -> DemoCase:
        if field_name not in REQUIRED_FIELDS:
            raise KeyError(f"unknown field {field_name}")
        async with self._lock:
            case = self._repo.get()
            if case.extracted_income is None:
                raise RuntimeError("no extraction to edit")
            field = getattr(case.extracted_income, field_name)
            if field.original_value is None:
                field.original_value = field.value
            field.value = new_value
            field.normalized_value = _normalize_for(field_name, new_value)
            field.provenance = Provenance.human_approved
            field.confidence = 1.0
            case.review_record = case.review_record or ReviewRecord()
            if field_name not in case.review_record.edited_fields:
                case.review_record.edited_fields.append(field_name)
            self._repo.set(case)
        await self._bus.emit(
            event_type="document.review_edit", label=f"Reviewer edited {field_name}",
            status=EventStatus.info, service="Document review",
        )
        return self._repo.get()

    async def review_approve(self) -> DemoCase:
        async with self._lock:
            case = self._repo.get()
            inc = case.extracted_income
            if inc is None:
                raise RuntimeError("no extraction to approve")
            missing = [
                n for n, f in _fields(inc).items()
                if f.value is None or _normalize_for(n, f.value) in (None, "")
            ]
            if missing:
                raise ValueError(f"cannot approve; unresolved fields: {', '.join(missing)}")
            edited = bool(case.review_record and case.review_record.edited_fields)
            case.accepted_income = _build_accepted(
                inc, Provenance.human_approved if edited else Provenance.extracted
            )
            case.document_state = DocumentState.accepted_after_review
            case.review_record = case.review_record or ReviewRecord()
            case.review_record.decision = "approved"
            case.review_record.resolved_at = _now()
            self._repo.set(case)
        await self._bus.emit(
            event_type="document.accepted_after_review", label="Reviewer approved income",
            status=EventStatus.completed, service="Document review",
        )
        return self._repo.get()

    async def review_reject(self) -> DemoCase:
        async with self._lock:
            case = self._repo.get()
            case.accepted_income = None
            case.document_state = DocumentState.rejected_by_reviewer
            case.review_record = case.review_record or ReviewRecord()
            case.review_record.decision = "rejected"
            case.review_record.resolved_at = _now()
            self._repo.set(case)
        await self._bus.emit(
            event_type="document.rejected", label="Reviewer rejected document",
            status=EventStatus.blocked, service="Document review",
        )
        return self._repo.get()

    async def remove(self) -> DemoCase:
        async with self._lock:
            case = self._repo.get()
            case.uploaded_document = None
            case.extracted_income = None
            case.accepted_income = None
            case.review_record = None
            case.document_state = DocumentState.empty
            case.capacity_result = None
            case.advisor_summary = None
            case.outcome = CaseOutcome.open
            self._repo.set(case)
        await self._bus.emit(
            event_type="document.removed",
            label="Customer removed payslip",
            status=EventStatus.info,
            service="Document analysis",
        )
        return self._repo.get()


def _normalize_for(field_name: str, value: str):
    if field_name in ("gross_salary_monthly", "net_salary_monthly"):
        return _parse_amount(value)
    if field_name == "pay_date":
        d = _parse_date(value)
        return d.isoformat() if d else None
    return value.strip() if isinstance(value, str) else value


def _build_accepted(inc: ExtractedIncome, provenance: Provenance) -> AcceptedIncome:
    gross = _parse_amount(inc.gross_salary_monthly.normalized_value or inc.gross_salary_monthly.value)
    net = _parse_amount(inc.net_salary_monthly.normalized_value or inc.net_salary_monthly.value)
    pay = _parse_date(inc.pay_date.normalized_value or inc.pay_date.value)
    return AcceptedIncome(
        employer_name=(inc.employer_name.value or "").strip(),
        gross_salary_monthly=gross or 0,
        net_salary_monthly=net or 0,
        employment_type=str(inc.employment_type.normalized_value or inc.employment_type.value or ""),
        pay_date=pay or date(1970, 1, 1),
        provenance=provenance,
        accepted_at=_now(),
    )
