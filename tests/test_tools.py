"""Dispatcher end-to-end: guards, consent gating, golden calc, idempotency."""
from __future__ import annotations

from app.domain.fixtures import MASTERCARD_ID, apply_accepted_income_emma
from app.domain.models import CardStatus, ConsentAction, IdentityStatus


async def _identify(stack) -> None:
    out = await stack.tools.dispatch(
        "identify_customer_with_digitald", {"approval_token": "demo-token"}
    )
    assert out.ok and stack.repo.get().identity_status is IdentityStatus.identified


async def _grant(stack, action, scope=None) -> str:
    rec = await stack.tools.request_consent(action, resource_scope=scope)
    await stack.tools.resolve_consent(rec.consent_id, "yes, go ahead")
    return rec.consent_id


# ---- guards ------------------------------------------------------------- #
async def test_crm_blocked_before_identify(stack):
    case = stack.repo.get()
    case.identity_status = IdentityStatus.unidentified
    stack.repo.set(case)
    out = await stack.tools.dispatch("get_crm_profile", {})
    assert not out.ok
    assert "tool.blocked_by_policy" in stack.event_types()


async def test_credit_blocked_without_consent(stack):
    await _identify(stack)
    out = await stack.tools.dispatch(
        "run_credit_check", {"customerId": stack.repo.get().customer_profile.customer_id}
    )
    assert not out.ok and out.result["error"] == "consent_required"
    assert out.result["code"] == "blocked:missing_consent"
    assert stack.repo.get().credit_result is None
    assert stack.bus.history()[-1].display.label == "blocked:missing_consent"


async def test_calculate_blocked_without_income(stack):
    await _identify(stack)
    await _grant(stack, ConsentAction.credit_check)
    await stack.tools.dispatch(
        "run_credit_check", {"customerId": stack.repo.get().customer_profile.customer_id}
    )
    out = await stack.tools.dispatch(
        "calculate_borrowing_capacity", {"property_price": 7_000_000, "deposit": 1_750_000}
    )
    assert not out.ok  # accepted income missing


async def test_phone_number_update_is_validated_and_persisted(stack):
    await _identify(stack)
    invalid = await stack.tools.dispatch(
        "update_customer_phone_number", {"phone_number": "123"}
    )
    assert not invalid.ok and invalid.result["error"] == "invalid_input"

    updated = await stack.tools.dispatch(
        "update_customer_phone_number", {"phone_number": "070-987 65 43"}
    )
    assert updated.ok
    assert updated.result["phone_number"] == "+46 70 987 65 43"
    profile = stack.repo.get().customer_profile
    assert profile.phone_number == "+46 70 987 65 43"
    assert profile.contact_details_updated_by == "Voice assistant"
    assert "Update phone number" in [
        event.display.label for event in stack.bus.history()
    ]

    await stack.reset()
    assert stack.repo.get().customer_profile.phone_number == "+46 70 123 45 67"


# ---- happy path --------------------------------------------------------- #
async def test_full_mortgage_and_card_flow(stack):
    await _identify(stack)

    crm = await stack.tools.dispatch("get_crm_profile", {})
    assert crm.ok and crm.result["employer_name"] == "Northstar AB"

    # M3 stand-in: accepted income present on the case.
    case = stack.repo.get()
    apply_accepted_income_emma(case)
    stack.repo.set(case)

    await _grant(stack, ConsentAction.credit_check)
    credit = await stack.tools.dispatch(
        "run_credit_check", {"customerId": stack.repo.get().customer_profile.customer_id}
    )
    assert credit.ok and credit.result["creditScore"] == 781
    assert credit.result["paymentRemarks"] == []
    assert credit.result["existingCommitments"][0]["monthlyPayment"] == 4_200
    assert credit.consent_consumed is not None

    # Second credit check is idempotent and needs no new consent.
    again = await stack.tools.dispatch(
        "run_credit_check", {"customerId": stack.repo.get().customer_profile.customer_id}
    )
    assert again.ok and again.idempotent_replay

    cap = await stack.tools.dispatch(
        "calculate_borrowing_capacity",
        {"purchasePrice": 7_000_000, "deposit": 1_750_000, "location": "Täby"},
    )
    assert cap.ok
    assert cap.result["netAfterStress"] == 15_575
    assert cap.result["dtiRatio"] == 4.71
    assert cap.result["dtiFlag"] == "above_soft_guideline"
    assert cap.result["verdict"] == "affordable_with_note"

    summary = await stack.tools.dispatch(
        "write_advisor_summary", {"caseId": stack.repo.get().case_id}
    )
    assert summary.ok
    assert summary.result["flags"] == ["dti_above_guideline"]
    assert summary.result["recommendedAction"] == "advisor_review"
    assert "approv" not in summary.result["summary"].lower()

    # Meeting: first near-term availability, then after 3-week reschedule.
    near = await stack.tools.dispatch(
        "get_available_meeting_times", {"earliest_date": "2026-08-24"}
    )
    assert near.ok
    later = await stack.tools.dispatch(
        "get_available_meeting_times", {"earliest_date": "2026-09-21"}
    )
    slot_ids = [s["slot_id"] for s in later.result["slots"]]
    assert "slot-2026-09-21-1500" in slot_ids

    booked = await stack.tools.dispatch(
        "book_meeting", {"slot_id": "slot-2026-09-21-1500", "purpose": "Mortgage"}
    )
    assert booked.ok and booked.result["booking_reference"].startswith("BKG-")
    ref = booked.result["booking_reference"]
    # Idempotent re-book of the same slot.
    rebook = await stack.tools.dispatch("book_meeting", {"slot_id": "slot-2026-09-21-1500"})
    assert rebook.idempotent_replay
    assert stack.repo.get().booked_meeting.booking_reference == ref

    # Part 2: cards + stolen-card block.
    cards = await stack.tools.dispatch("get_customer_cards", {})
    assert cards.ok and cards.result["cards"][0]["last_four"] == "4471"
    assert cards.result["cards"][1]["last_four"] == "1842"

    # The customer's original request is sufficient; no second consent record is required.
    blocked = await stack.tools.dispatch(
        "block_card_and_order_replacement", {"card_id": MASTERCARD_ID, "reason": "stolen"}
    )
    assert blocked.ok and blocked.result["blocked"] is True
    order_ref = blocked.result["replacement_order_reference"]

    # Idempotent re-block returns the same order, no new consent.
    reblock = await stack.tools.dispatch(
        "block_card_and_order_replacement", {"card_id": MASTERCARD_ID, "reason": "stolen"}
    )
    assert reblock.idempotent_replay
    assert reblock.result["replacement_order_reference"] == order_ref
    assert stack.repo.get().cards[0].status is CardStatus.blocked


async def test_block_unknown_card_is_refused(stack):
    await _identify(stack)
    out = await stack.tools.dispatch(
        "block_card_and_order_replacement", {"card_id": "card-OTHER", "reason": "stolen"}
    )
    assert not out.ok


async def test_reset_discards_consent(stack):
    await _identify(stack)
    await _grant(stack, ConsentAction.credit_check)
    await stack.reset()
    # New epoch/case: known demo identity remains, consent is gone.
    assert stack.repo.get().identity_status is IdentityStatus.identified
    out = await stack.tools.dispatch(
        "run_credit_check", {"customerId": stack.repo.get().customer_profile.customer_id}
    )
    assert not out.ok


async def test_within_guideline_clears_summary_flag(stack):
    await _identify(stack)
    case = stack.repo.get()
    apply_accepted_income_emma(case)
    stack.repo.set(case)
    await _grant(stack, ConsentAction.credit_check)
    await stack.tools.dispatch(
        "run_credit_check", {"customerId": stack.repo.get().customer_profile.customer_id}
    )
    cap = await stack.tools.dispatch(
        "calculate_borrowing_capacity",
        {"purchasePrice": 4_000_000, "deposit": 2_000_000},
    )
    summary = await stack.tools.dispatch(
        "write_advisor_summary", {"caseId": stack.repo.get().case_id}
    )

    assert cap.result["dtiFlag"] == "within_guideline"
    assert summary.result["flags"] == []
    assert summary.result["recommendedAction"] == "standard_review"


async def test_check_income_status_reports_rejected_then_verified(stack):
    await _identify(stack)
    # Fresh canonical case: Emma's payslip is seeded as auto-rejected (blurred scan).
    rejected = await stack.tools.dispatch("check_income_status", {})
    assert rejected.ok
    assert rejected.result["income_verified"] is False
    assert rejected.result["document_state"] == "analysis_failed"
    assert rejected.result["rejection_reason"]
    assert "re-upload" in rejected.summary.lower()

    # After a clean payslip is accepted, the same read reports income verified.
    case = stack.repo.get()
    apply_accepted_income_emma(case)
    stack.repo.set(case)
    verified = await stack.tools.dispatch("check_income_status", {})
    assert verified.ok
    assert verified.result["income_verified"] is True
    assert verified.result["document_state"] == "accepted_automatically"
    assert verified.result["rejection_reason"] is None
    assert verified.result["net_salary_monthly"] == 62_400
    assert "covered" in verified.summary.lower()
    assert verified.label == "Check income status"


async def test_check_income_status_requires_identity(stack):
    case = stack.repo.get()
    case.identity_status = IdentityStatus.unidentified
    stack.repo.set(case)
    out = await stack.tools.dispatch("check_income_status", {})
    assert not out.ok
    assert "tool.blocked_by_policy" in stack.event_types()
