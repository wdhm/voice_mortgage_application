"""Document flow: confidence policy, both samples to terminal states, review, reuse."""
from __future__ import annotations

import pytest

from app.documents.samples import render_payslip_html
from app.documents.service import DocumentService
from app.documents.simulated import SimulatedDocumentAnalyzer
from app.domain.consent import ConsentEngine
from app.domain.fixtures import CASE_ID
from app.domain.models import ConsentAction, DocumentState, IdentityStatus, Provenance
from app.domain.repository import InMemoryCaseRepository
from app.events.bus import EventBus
from app.tools.dispatcher import ToolDispatcher


class DocStack:
    def __init__(self) -> None:
        self.repo = InMemoryCaseRepository(session_id="session-test")
        self.bus = EventBus(session_id="session-test", case_id=CASE_ID)
        self.bus.set_epoch(self.repo.epoch)
        self.docs = DocumentService(self.repo, self.bus, SimulatedDocumentAnalyzer())
        self.tools = ToolDispatcher(self.repo, self.bus, ConsentEngine())

    async def analyze_sample(self, key: str):
        html = render_payslip_html(key).encode()
        return await self.docs.analyze(
            content=html, content_type="text/html", filename=f"{key}.html", sample_key=key
        )


@pytest.fixture
def d() -> DocStack:
    return DocStack()


async def test_high_confidence_auto_accepts(d):
    case = await d.analyze_sample("high_confidence")
    assert case.document_state is DocumentState.accepted_automatically
    assert case.accepted_income is not None
    assert case.accepted_income.gross_salary_monthly == 96_000
    assert case.accepted_income.net_salary_monthly == 62_400
    assert case.accepted_income.provenance is Provenance.extracted


async def test_low_confidence_routes_to_review(d):
    case = await d.analyze_sample("low_confidence")
    assert case.document_state is DocumentState.review_required
    assert case.accepted_income is None
    # Net pay + employment type + pay date fall below threshold.
    assert case.extracted_income.net_salary_monthly.confidence < 0.85
    assert case.extracted_income.employment_type.confidence < 0.85


async def test_uploaded_document_returns_demo_extraction_for_review(d):
    case = await d.docs.analyze(
        content=b"%PDF-demo", content_type="application/pdf", filename="emma-payslip.pdf"
    )
    assert case.document_state is DocumentState.review_required
    assert case.uploaded_document.filename == "emma-payslip.pdf"
    assert case.extracted_income.employer_name.value == "Northstar AB"
    assert case.accepted_income is None


async def test_uploading_bundled_payslip_pdf_auto_accepts(d):
    # Uploading the genuine committed payslip PDF (no sample_key) is routed by an
    # exact content hash to the high-confidence straight-through path.
    from app.documents.samples import sample_pdf_path

    pdf = sample_pdf_path("high_confidence")
    assert pdf is not None, "committed high-confidence PDF asset is expected to exist"
    case = await d.docs.analyze(
        content=pdf.read_bytes(),
        content_type="application/pdf",
        filename=pdf.name,
        sample_key=None,
    )
    assert case.document_state is DocumentState.accepted_automatically
    assert case.uploaded_document.sample_key is None
    assert case.accepted_income is not None
    assert case.accepted_income.gross_salary_monthly == 96_000
    assert case.accepted_income.net_salary_monthly == 62_400


async def test_review_edit_retains_original_and_sets_provenance(d):
    await d.analyze_sample("low_confidence")
    case = await d.docs.review_edit("net_salary_monthly", "62 400 kr")
    field = case.extracted_income.net_salary_monthly
    assert field.original_value == "6? 400 kr"
    assert field.normalized_value == 62_400
    assert field.provenance is Provenance.human_approved
    assert "net_salary_monthly" in case.review_record.edited_fields


async def test_review_approve_after_edits(d):
    await d.analyze_sample("low_confidence")
    await d.docs.review_edit("net_salary_monthly", "62 400 kr")
    await d.docs.review_edit("employment_type", "permanent_full_time")
    await d.docs.review_edit("pay_date", "2026-08-25")
    case = await d.docs.review_approve()
    assert case.document_state is DocumentState.accepted_after_review
    assert case.accepted_income.net_salary_monthly == 62_400
    assert case.accepted_income.provenance is Provenance.human_approved


async def test_review_reject_saves_no_income(d):
    await d.analyze_sample("low_confidence")
    case = await d.docs.review_reject()
    assert case.document_state is DocumentState.rejected_by_reviewer
    assert case.accepted_income is None


async def test_epoch_guard_discards_result_when_reset_lands_mid_analysis(d):
    # An analyzer that resets the case *during* analysis simulates a demo reset
    # racing an in-flight extraction; the stale result must be discarded.
    from app.documents.port import AnalyzerResult, FieldExtraction

    class ResettingAnalyzer:
        provider = "simulated"

        async def analyze(self, **_):
            d.repo.reset()  # epoch bumps while analysis is "in flight"
            return AnalyzerResult(
                provider="simulated", analyzer_id="x", method="test",
                fields={"employer_name": FieldExtraction("X", "X", 0.99, None)},
            )

    d.docs._analyzer = ResettingAnalyzer()
    before_epoch = d.repo.epoch
    case = await d.docs.analyze(
        content=b"x", content_type="text/html", filename="x.html", sample_key="high_confidence"
    )
    assert d.repo.epoch == before_epoch + 1  # reset happened
    assert case.accepted_income is None       # stale result discarded
    assert case.extracted_income is None
    assert case.document_state is DocumentState.empty


async def test_accepted_income_feeds_golden_calc(d):
    # Full bridge: auto-accepted income -> identified -> credit -> capacity golden.
    await d.analyze_sample("high_confidence")
    await d.tools.dispatch("identify_customer_with_digitald", {"approval_token": "demo-token"})
    rec = await d.tools.request_consent(ConsentAction.credit_check)
    await d.tools.resolve_consent(rec.consent_id, "yes, go ahead")
    await d.tools.dispatch("run_credit_check", {})
    cap = await d.tools.dispatch(
        "calculate_borrowing_capacity", {"property_price": 7_000_000, "deposit": 1_750_000}
    )
    assert cap.ok
    assert cap.result["metrics"]["kalp_surplus_monthly"] == 5_138
    assert cap.result["outcome"] == "preliminary_positive"
    assert d.repo.get().identity_status is IdentityStatus.identified
