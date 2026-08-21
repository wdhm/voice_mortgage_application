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
    out = await stack.tools.dispatch("run_credit_check", {})
    assert not out.ok and out.result["error"] == "consent_required"
    assert stack.repo.get().credit_result is None


async def test_calculate_blocked_without_income(stack):
    await _identify(stack)
    await _grant(stack, ConsentAction.credit_check)
    await stack.tools.dispatch("run_credit_check", {})
    out = await stack.tools.dispatch(
        "calculate_borrowing_capacity", {"property_price": 7_000_000, "deposit": 1_750_000}
    )
    assert not out.ok  # accepted income missing


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
    credit = await stack.tools.dispatch("run_credit_check", {})
    assert credit.ok and credit.result["score"] == 781
    assert credit.consent_consumed is not None

    # Second credit check is idempotent and needs no new consent.
    again = await stack.tools.dispatch("run_credit_check", {})
    assert again.ok and again.idempotent_replay

    cap = await stack.tools.dispatch(
        "calculate_borrowing_capacity",
        {"property_price": 7_000_000, "deposit": 1_750_000, "location": "Täby"},
    )
    assert cap.ok
    assert cap.result["metrics"]["kalp_surplus_monthly"] == 5_138
    assert cap.result["outcome"] == "preliminary_positive"

    summary = await stack.tools.dispatch("write_advisor_summary", {})
    assert summary.ok
    assert "supportable" in summary.result["status_text"].lower()
    assert "approv" not in summary.result["status_text"].lower()
    assert summary.result["final_decision_required"] is True

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

    # Block without consent is refused.
    refused = await stack.tools.dispatch(
        "block_card_and_order_replacement", {"card_id": MASTERCARD_ID, "reason": "stolen"}
    )
    assert not refused.ok

    await _grant(stack, ConsentAction.block_card, scope=MASTERCARD_ID)
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


async def test_block_consent_wrong_card_scope_refused(stack):
    await _identify(stack)
    # Consent granted for a different card must not authorize 4471.
    await _grant(stack, ConsentAction.block_card, scope="card-OTHER")
    out = await stack.tools.dispatch(
        "block_card_and_order_replacement", {"card_id": MASTERCARD_ID, "reason": "stolen"}
    )
    assert not out.ok and out.result["error"] == "consent_required"


async def test_reset_discards_consent(stack):
    await _identify(stack)
    await _grant(stack, ConsentAction.credit_check)
    await stack.reset()
    # New epoch/case: known demo identity remains, consent is gone.
    assert stack.repo.get().identity_status is IdentityStatus.identified
    out = await stack.tools.dispatch("run_credit_check", {})
    assert not out.ok
