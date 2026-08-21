"""The nine deterministic demo tools.

Each handler mutates the DemoCase in place and returns a ToolOutcome. Guards
raise GuardError; protected tools call ConsentEngine.consume (which raises
ConsentRequired) BEFORE any state change. All outputs are canonical and fixed so
a recorded demo replays identically. No handler lets the model compute figures.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta

from ..domain.calculator import CapacityInputs, compute_capacity
from ..domain.consent import ConsentEngine
from ..domain.models import (
    AdvisorSummary,
    BookedMeeting,
    CapacityResult,
    CardStatus,
    ConsentAction,
    CreditResult,
    DemoCase,
    IdentityStatus,
    MeetingSlot,
    ReplacementOrder,
)
from ..events.models import EventStatus
from .base import GuardError, ToolInputError, ToolOutcome

_TZ = "Europe/Stockholm"


def _now() -> datetime:
    return datetime.now(UTC)


def _require_identified(case: DemoCase) -> None:
    if case.identity_status != IdentityStatus.identified:
        raise GuardError(
            "Customer must be identified first.", label="Blocked: identity required"
        )


# --------------------------------------------------------------------------- #
# 1. identify_customer_with_digitald
# --------------------------------------------------------------------------- #
def identify_customer_with_digitald(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    if case.identity_status == IdentityStatus.identified:
        return ToolOutcome(
            ok=True,
            result=_identity_result(case),
            summary=f"{case.customer_profile.display_name} is already identified.",
            service="DigitalD",
            label="Identify customer (DigitalD)",
            idempotent_replay=True,
        )
    if not args.get("approval_token"):
        raise GuardError(
            "DigitalD modal was not approved.", label="Blocked: DigitalD not approved"
        )
    case.identity_status = IdentityStatus.identified
    return ToolOutcome(
        ok=True,
        result=_identity_result(case),
        summary=f"Identity confirmed for {case.customer_profile.display_name} via DigitalD.",
        service="DigitalD",
        label="Identify customer (DigitalD)",
        status=EventStatus.granted,
    )


def _identity_result(case: DemoCase) -> dict:
    return {
        "customer_id": case.customer_profile.customer_id,
        "display_name": case.customer_profile.display_name,
        "identified_at": _now().isoformat(),
        "assurance": "high",
    }


# --------------------------------------------------------------------------- #
# 2. get_crm_profile
# --------------------------------------------------------------------------- #
def get_crm_profile(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    p = case.customer_profile
    return ToolOutcome(
        ok=True,
        result={
            "customer_id": p.customer_id,
            "display_name": p.display_name,
            "employer_name": p.employer_name,
            "relationship_summary": p.relationship_summary,
            "existing_car_loan_balance": p.existing_car_loan_balance,
            "existing_car_loan_payment": p.existing_car_loan_payment,
        },
        summary=f"{p.display_name}, {p.employer_name}. {p.relationship_summary}",
        service="Core banking",
        label="Get CRM profile",
    )


# --------------------------------------------------------------------------- #
# 3. run_credit_check  (protected: credit_check consent)
# --------------------------------------------------------------------------- #
def run_credit_check(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    if case.credit_result is not None:
        return ToolOutcome(
            ok=True,
            result=_credit_result_dict(case.credit_result),
            summary="Credit check already completed: score 781/999, risk low, no defaults.",
            service="UC credit bureau",
            label="Run credit check",
            idempotent_replay=True,
        )
    consumed = engine.consume(
        case,
        ConsentAction.credit_check,
        customer_id=case.customer_profile.customer_id,
        consent_id=args.get("consent_id"),
    )
    result = CreditResult(
        score=781,
        max_score=999,
        risk_band="low",
        existing_debt_balance=case.customer_profile.existing_car_loan_balance or 180_000,
        existing_debt_payment=case.customer_profile.existing_car_loan_payment or 4_200,
        defaults="none",
        source="mock_credit_bureau",
        checked_at=_now(),
    )
    case.credit_result = result
    return ToolOutcome(
        ok=True,
        result=_credit_result_dict(result),
        summary="Credit check complete: score 781/999, risk low, no defaults.",
        service="UC credit bureau",
        label="Run credit check",
        consent_consumed=consumed.consent_id,
    )


def _credit_result_dict(r: CreditResult) -> dict:
    return {
        "score": r.score,
        "max_score": r.max_score,
        "risk_band": r.risk_band,
        "existing_debt_balance": r.existing_debt_balance,
        "existing_debt_payment": r.existing_debt_payment,
        "defaults": r.defaults,
        "source": r.source,
    }


# --------------------------------------------------------------------------- #
# 4. calculate_borrowing_capacity
# --------------------------------------------------------------------------- #
def calculate_borrowing_capacity(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    if case.accepted_income is None:
        raise GuardError(
            "Accepted income is required before calculating capacity.",
            label="Blocked: income required",
        )
    if case.credit_result is None:
        raise GuardError(
            "A credit result is required before calculating capacity.",
            label="Blocked: credit result required",
        )
    price = _as_int(args.get("property_price"), "property_price")
    deposit = _as_int(args.get("deposit"), "deposit")
    if deposit > price:
        raise ToolInputError("Deposit cannot exceed the property price.")
    location = args.get("location") or (case.property_request.location if case.property_request else "")

    from ..domain.models import PropertyRequest

    case.property_request = PropertyRequest(location=location, purchase_price=price, deposit=deposit)

    comp = compute_capacity(
        CapacityInputs(
            property_price=price,
            deposit=deposit,
            gross_income_monthly=case.accepted_income.gross_salary_monthly,
            net_income_monthly=case.accepted_income.net_salary_monthly,
            existing_debt_balance=case.credit_result.existing_debt_balance,
            existing_debt_payment_monthly=case.credit_result.existing_debt_payment,
        )
    )
    case.capacity_result = CapacityResult(
        inputs=comp.inputs,
        metrics=comp.metrics,
        outcome=comp.outcome,
        assumptions=comp.assumptions,
        caveats=comp.caveats,
        calculated_at=_now(),
    )
    case.outcome = comp.outcome
    surplus = comp.metrics["kalp_surplus_monthly"]
    return ToolOutcome(
        ok=True,
        result={"metrics": comp.metrics, "outcome": comp.outcome.value},
        summary=(
            f"Preliminary and illustrative: monthly surplus about SEK {surplus:,} "
            f"(LTV {comp.metrics['ltv_pct']}%, debt ratio {comp.metrics['debt_ratio']}x). "
            "This is not a final decision."
        ),
        service="Affordability engine",
        label="Calculate borrowing capacity",
    )


def _as_int(value, name: str) -> int:
    if value is None:
        raise ToolInputError(f"Missing required input: {name}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolInputError(f"Invalid integer for {name}: {value!r}") from exc


# --------------------------------------------------------------------------- #
# 5. write_advisor_summary
# --------------------------------------------------------------------------- #
def write_advisor_summary(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    if not (case.accepted_income and case.credit_result and case.capacity_result):
        raise GuardError(
            "Income, credit result and capacity result are all required.",
            label="Blocked: summary preconditions",
        )
    inc = case.accepted_income
    cap = case.capacity_result
    sections = {
        "identity": {
            "customer": case.customer_profile.display_name,
            "assurance": "high",
        },
        "income_provenance": {
            "employer": inc.employer_name,
            "gross_monthly": inc.gross_salary_monthly,
            "net_monthly": inc.net_salary_monthly,
            "provenance": inc.provenance.value,
        },
        "requested_loan": case.property_request.model_dump() if case.property_request else {},
        "credit_result": _credit_result_dict(case.credit_result),
        "capacity_metrics": cap.metrics,
        "customer_preferences": {"meeting": args.get("preferences", "advisor follow-up")},
        "risks_caveats": cap.caveats,
        "meeting": case.booked_meeting.model_dump() if case.booked_meeting else None,
    }
    positive = cap.outcome.name == "preliminary_positive"
    summary_model = AdvisorSummary(
        sections=sections,
        final_decision_required=True,
        status_text=(
            "Preliminary assessment: looks supportable"
            if positive
            else "Preliminary assessment: needs advisor attention"
        ),
        decision_text="Final decision: advisor required",
        updated_at=_now(),
    )
    case.advisor_summary = summary_model
    return ToolOutcome(
        ok=True,
        result={
            "status_text": summary_model.status_text,
            "decision_text": summary_model.decision_text,
            "final_decision_required": True,
            "sections": list(sections.keys()),
        },
        summary="Advisor summary prepared. Final decision requires a Bank Alfa advisor.",
        service="Advisor handoff",
        label="Write advisor summary",
        status=EventStatus.review,
    )


# --------------------------------------------------------------------------- #
# 6. get_available_meeting_times
# --------------------------------------------------------------------------- #
def get_available_meeting_times(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    earliest = _parse_date(args.get("earliest_date"))
    preferred = (args.get("preferred_time") or "afternoon").lower()
    hour = {"morning": 9, "midday": 12, "afternoon": 15}.get(preferred, 15)

    monday = earliest + timedelta(days=(7 - earliest.weekday()) % 7)  # roll forward to Monday
    slots: list[MeetingSlot] = []
    for offset in (0, 2, 4):  # Mon / Wed / Fri that week
        day = monday + timedelta(days=offset)
        start = datetime.combine(day, time(hour, 0))
        slots.append(
            MeetingSlot(
                slot_id=f"slot-{day.isoformat()}-{hour:02d}00",
                start=start,
                end=start + timedelta(minutes=45),
                timezone=_TZ,
                advisor="Mortgage advisor",
            )
        )
    case.offered_meeting_slots = slots
    return ToolOutcome(
        ok=True,
        result={"slots": [_slot_dict(s) for s in slots]},
        summary="Offered "
        + ", ".join(s.start.strftime("%a %d %b %H:%M") for s in slots)
        + " (earliest available).",
        service="Advisor calendar",
        label="Get available meeting times",
    )


def _slot_dict(s: MeetingSlot) -> dict:
    return {
        "slot_id": s.slot_id,
        "start": s.start.isoformat(),
        "end": s.end.isoformat(),
        "timezone": s.timezone,
        "advisor": s.advisor,
    }


def _parse_date(value) -> date:
    if not value:
        raise ToolInputError("Missing required input: earliest_date")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ToolInputError(f"Invalid earliest_date: {value!r}") from exc


# --------------------------------------------------------------------------- #
# 7. book_meeting
# --------------------------------------------------------------------------- #
def book_meeting(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    slot_id = args.get("slot_id")
    if not slot_id:
        raise ToolInputError("Missing required input: slot_id")
    purpose = args.get("purpose") or "Mortgage advisory meeting"

    if case.booked_meeting is not None:
        if case.booked_meeting.slot.slot_id == slot_id:
            return ToolOutcome(
                ok=True,
                result=_booking_dict(case.booked_meeting),
                summary=f"Meeting already booked for {case.booked_meeting.slot.start.strftime('%a %d %b %H:%M')}.",
                service="Advisor calendar",
                label="Book meeting",
                idempotent_replay=True,
            )
        raise GuardError(
            "A different meeting is already booked; fetch availability again.",
            label="Blocked: meeting already booked",
        )

    slot = next((s for s in case.offered_meeting_slots if s.slot_id == slot_id), None)
    if slot is None:
        raise GuardError(
            "That slot was not offered in this session.", label="Blocked: slot not offered"
        )
    booking = BookedMeeting(
        slot=slot,
        purpose=purpose,
        booking_reference=f"BKG-{uuid.uuid4().hex[:8].upper()}",
        booked_at=_now(),
    )
    case.booked_meeting = booking
    return ToolOutcome(
        ok=True,
        result=_booking_dict(booking),
        summary=f"Booked {slot.start.strftime('%a %d %b %H:%M')}-{slot.end.strftime('%H:%M')} {slot.timezone}.",
        service="Advisor calendar",
        label="Book meeting",
    )


def _booking_dict(b: BookedMeeting) -> dict:
    return {
        "slot": _slot_dict(b.slot),
        "purpose": b.purpose,
        "booking_reference": b.booking_reference,
    }


# --------------------------------------------------------------------------- #
# 8. get_customer_cards
# --------------------------------------------------------------------------- #
def get_customer_cards(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    cards = [
        {
            "card_id": c.card_id,
            "card_type": c.card_type,
            "last_four": c.last_four,
            "status": c.status.value,
        }
        for c in case.cards
    ]
    return ToolOutcome(
        ok=True,
        result={"cards": cards},
        summary="; ".join(f"{c['card_type']} ****{c['last_four']} ({c['status']})" for c in cards),
        service="Card services",
        label="Get customer cards",
    )


# --------------------------------------------------------------------------- #
# 9. block_card_and_order_replacement  (protected: block_card consent, card-scoped)
# --------------------------------------------------------------------------- #
def block_card_and_order_replacement(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    card_id = args.get("card_id")
    if not card_id:
        raise ToolInputError("Missing required input: card_id")
    card = next((c for c in case.cards if c.card_id == card_id), None)
    if card is None:
        raise GuardError("Unknown card.", label="Blocked: unknown card")
    reason = args.get("reason") or "stolen"

    if card.status == CardStatus.blocked and case.replacement_order is not None:
        return ToolOutcome(
            ok=True,
            result=_block_result(card, case.replacement_order),
            summary=f"Card ****{card.last_four} is already blocked; replacement {case.replacement_order.order_reference} on the way.",
            service="Card services",
            label="Block card & order replacement",
            idempotent_replay=True,
        )

    consumed = engine.consume(
        case,
        ConsentAction.block_card,
        resource_scope=card_id,
        customer_id=case.customer_profile.customer_id,
        consent_id=args.get("consent_id"),
    )
    card.status = CardStatus.blocked
    order = ReplacementOrder(
        order_reference=f"RPL-{uuid.uuid4().hex[:8].upper()}",
        card_id=card_id,
        reason=reason,
        delivery_estimate="3-5 business days to your registered address",
        ordered_at=_now(),
    )
    case.replacement_order = order
    return ToolOutcome(
        ok=True,
        result=_block_result(card, order),
        summary=f"Card ****{card.last_four} blocked and replacement {order.order_reference} ordered.",
        service="Card services",
        label="Block card & order replacement",
        status=EventStatus.granted,
        consent_consumed=consumed.consent_id,
    )


def _block_result(card, order: ReplacementOrder) -> dict:
    return {
        "card_id": card.card_id,
        "last_four": card.last_four,
        "status": card.status.value,
        "blocked": card.status == CardStatus.blocked,
        "replacement_order_reference": order.order_reference,
        "delivery_estimate": order.delivery_estimate,
    }


# Registry name -> handler.
HANDLERS = {
    "identify_customer_with_digitald": identify_customer_with_digitald,
    "get_crm_profile": get_crm_profile,
    "run_credit_check": run_credit_check,
    "calculate_borrowing_capacity": calculate_borrowing_capacity,
    "write_advisor_summary": write_advisor_summary,
    "get_available_meeting_times": get_available_meeting_times,
    "book_meeting": book_meeting,
    "get_customer_cards": get_customer_cards,
    "block_card_and_order_replacement": block_card_and_order_replacement,
}
