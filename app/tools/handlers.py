"""The deterministic demo tools.

Each handler mutates the DemoCase in place and returns a ToolOutcome. Guards
raise GuardError; protected tools call ConsentEngine.consume (which raises
ConsentRequired) BEFORE any state change. All outputs are canonical and fixed so
a recorded demo replays identically. No handler lets the model compute figures.
"""
from __future__ import annotations

import re
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
    DocumentState,
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
            "customer_number": p.customer_number,
            "display_name": p.display_name,
            "phone_number": p.phone_number,
            "email": p.email,
            "address": {
                "street": p.street_address,
                "postal_code": p.postal_code,
                "city": p.city,
                "country": p.country,
            },
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
# 3. update_customer_phone_number
# --------------------------------------------------------------------------- #
def _normalize_swedish_phone_number(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ToolInputError("A new phone number is required.")

    compact = re.sub(r"[\s().-]", "", raw.strip())
    if compact.startswith("0046"):
        compact = f"+46{compact[4:]}"
    elif compact.startswith("0"):
        compact = f"+46{compact[1:]}"

    if not re.fullmatch(r"\+46\d{7,10}", compact):
        raise ToolInputError(
            "Enter a valid Swedish phone number, for example +46 70 123 45 67."
        )

    national = compact[3:]
    groups = [national[:2]]
    remaining = national[2:]
    while remaining:
        groups.append(remaining[:3] if len(remaining) % 2 == 1 else remaining[:2])
        remaining = remaining[len(groups[-1]):]
    return "+46 " + " ".join(groups)


def update_customer_phone_number(
    engine: ConsentEngine, case: DemoCase, args: dict
) -> ToolOutcome:
    _require_identified(case)
    phone_number = _normalize_swedish_phone_number(args.get("phone_number"))
    profile = case.customer_profile

    if profile.phone_number == phone_number:
        return ToolOutcome(
            ok=True,
            result={"phone_number": phone_number, "changed": False},
            summary=f"The registered phone number is already {phone_number}.",
            service="Customer profile",
            label="Update phone number",
            idempotent_replay=True,
        )

    profile.phone_number = phone_number
    profile.contact_details_updated_at = _now()
    profile.contact_details_updated_by = "Voice assistant"
    return ToolOutcome(
        ok=True,
        result={
            "phone_number": phone_number,
            "changed": True,
            "updated_at": profile.contact_details_updated_at.isoformat(),
            "updated_by": profile.contact_details_updated_by,
        },
        summary=f"Phone number updated to {phone_number}.",
        service="Customer profile",
        label="Update phone number",
    )


# --------------------------------------------------------------------------- #
# 4. run_credit_check  (protected: credit_check consent)
# --------------------------------------------------------------------------- #
def run_credit_check(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    _require_identified(case)
    customer_id = args.get("customerId") or args.get("customer_id")
    if customer_id != case.customer_profile.customer_id:
        raise ToolInputError("customerId must match the identified customer.")
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
        "creditScore": r.score,
        "maxScore": r.max_score,
        "riskBand": r.risk_band,
        "paymentRemarks": [] if r.defaults == "none" else [r.defaults],
        "existingCommitments": [
            {
                "type": "car_loan",
                "balance": r.existing_debt_balance,
                "monthlyPayment": r.existing_debt_payment,
            }
        ],
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
    price = _as_int(args.get("purchasePrice", args.get("property_price")), "purchasePrice")
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
    return ToolOutcome(
        ok=True,
        result={
            "requestedMortgage": comp.metrics["requested_mortgage"],
            "ltv": comp.metrics["ltv"],
            "amortizationTier": comp.metrics["amortization_tier"],
            "stressTestRate": comp.metrics["stress_test_rate"],
            "monthlyStressedPayment": comp.metrics["monthly_stressed_payment"],
            "netAfterStress": comp.metrics["net_after_stress"],
            "dtiRatio": comp.metrics["dti_ratio"],
            "dtiFlag": comp.metrics["dti_flag"],
            "verdict": comp.metrics["verdict"],
        },
        summary=(
            f"At a 7% stress rate, the monthly amount remaining is about SEK "
            f"{comp.metrics['net_after_stress']:,}. "
            f"Debt-to-income is {comp.metrics['dti_ratio']}x. "
            "This is preliminary; a human advisor makes the final decision."
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
    case_id = args.get("caseId") or args.get("case_id")
    if case_id != case.case_id:
        raise ToolInputError("caseId must match the active mortgage case.")
    if not (case.accepted_income and case.credit_result and case.capacity_result):
        raise GuardError(
            "Income, credit result and capacity result are all required.",
            label="Blocked: summary preconditions",
        )
    inc = case.accepted_income
    cap = case.capacity_result
    dti_flagged = cap.metrics.get("dti_flag") == "above_soft_guideline"
    flags = ["dti_above_guideline"] if dti_flagged else []
    recommended_action = "advisor_review" if dti_flagged else "standard_review"
    verdict = cap.metrics.get("verdict")
    summary_text = (
        "Affordable under the 7% stress test"
        if verdict != "not_affordable_at_stress_rate"
        else "Not affordable under the 7% stress test"
    )
    if dti_flagged:
        summary_text += f"; DTI {cap.metrics['dti_ratio']}x is above the 4.5x soft guideline"
    summary_text += ". Human advisor decision required."
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
        summary=summary_text,
        flags=flags,
        recommended_action=recommended_action,
        final_decision_required=True,
        status_text=(
            "Preliminary assessment: affordable with advisor note"
            if dti_flagged and positive
            else "Preliminary assessment: affordable at stress rate"
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
            "summary": summary_model.summary,
            "flags": summary_model.flags,
            "recommendedAction": summary_model.recommended_action,
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
    full_month = args.get("full_month") is True

    month_slots = _monthly_meeting_slots(earliest)
    if full_month:
        slots = month_slots
    else:
        hour_range = {
            "morning": range(8, 12),
            "midday": range(11, 15),
            "afternoon": range(13, 17),
        }.get(preferred, range(13, 17))
        slots = [
            slot
            for slot in month_slots
            if slot.start.date() >= earliest and slot.start.hour in hour_range
        ][:5]
    offered_by_id = {slot.slot_id: slot for slot in case.offered_meeting_slots}
    offered_by_id.update({slot.slot_id: slot for slot in slots})
    case.offered_meeting_slots = sorted(offered_by_id.values(), key=lambda slot: slot.start)
    summary = (
        f"Selected weekday appointments are available between 08:00 and 17:00 in "
        f"{earliest.strftime('%B %Y')}."
        if full_month
        else "Offered "
        + ", ".join(s.start.strftime("%a %d %b %H:%M") for s in slots)
        + " (earliest available)."
    )
    return ToolOutcome(
        ok=True,
        result={"slots": [_slot_dict(s) for s in slots]},
        summary=summary,
        service="Advisor calendar",
        label="Get available meeting times",
    )


def _monthly_meeting_slots(month: date) -> list[MeetingSlot]:
    slots: list[MeetingSlot] = []
    day = month.replace(day=1)
    while day.month == month.month:
        week_index = (day.day - 1) // 7
        available_weekdays = {0, 2, 4} if week_index % 2 == 0 else {1, 3}
        if day.weekday() in available_weekdays:
            hours = {
                0: (8, 11, 15),
                1: (9, 13, 16),
                2: (10, 14),
            }[day.day % 3]
            for slot_hour in hours:
                start = datetime.combine(day, time(slot_hour, 0))
                slots.append(
                    MeetingSlot(
                        slot_id=f"slot-{day.isoformat()}-{slot_hour:02d}00",
                        start=start,
                        end=start + timedelta(minutes=45),
                        timezone=_TZ,
                        advisor="Mortgage advisor",
                    )
                )
        day += timedelta(days=1)
    return slots


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
# 9. block_card_and_order_replacement
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
        status=EventStatus.completed,
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


# --------------------------------------------------------------------------- #
# 10. check_income_status  (read-only: report the payslip / income state)
# --------------------------------------------------------------------------- #
_ACCEPTED_DOC_STATES = {
    DocumentState.accepted_automatically,
    DocumentState.accepted_after_review,
}


def check_income_status(engine: ConsentEngine, case: DemoCase, args: dict) -> ToolOutcome:
    """Report whether the customer's uploaded payslip is accepted and income verified.

    Read-only and consent-free. Lets the agent confirm — with a genuine, trace-visible
    read of case state — that a re-uploaded payslip is now readable/green, so it can tell
    the customer the income requirement for her mortgage application is covered.
    """
    _require_identified(case)
    state = case.document_state
    accepted = state in _ACCEPTED_DOC_STATES
    income = case.accepted_income
    result = {
        "document_state": state.value,
        "income_verified": accepted,
        "rejection_reason": case.rejection_reason,
        "employer_name": income.employer_name if income else None,
        "gross_salary_monthly": income.gross_salary_monthly if income else None,
        "net_salary_monthly": income.net_salary_monthly if income else None,
    }
    if accepted:
        summary = (
            "Payslip accepted — income is verified. The income requirement for the "
            "mortgage application is covered."
        )
    elif state == DocumentState.analysis_failed:
        reason = case.rejection_reason or "the payslip could not be read."
        nudge = "Ask the customer to re-upload a clear copy."
        summary = f"Payslip not accepted — {reason}"
        if nudge.lower() not in reason.lower():
            summary = f"{summary} {nudge}"
    elif state == DocumentState.empty:
        summary = "No payslip has been uploaded yet. Ask the customer to upload a payslip."
    elif state == DocumentState.review_required:
        summary = "Payslip is awaiting human review; income is not yet verified."
    else:
        summary = f"Payslip status: {state.value}; income is not yet verified."
    return ToolOutcome(
        ok=True,
        result=result,
        summary=summary,
        service="Document intelligence",
        label="Check income status",
    )


# Registry name -> handler.
HANDLERS = {
    "identify_customer_with_digitald": identify_customer_with_digitald,
    "get_crm_profile": get_crm_profile,
    "update_customer_phone_number": update_customer_phone_number,
    "run_credit_check": run_credit_check,
    "calculate_borrowing_capacity": calculate_borrowing_capacity,
    "write_advisor_summary": write_advisor_summary,
    "get_available_meeting_times": get_available_meeting_times,
    "book_meeting": book_meeting,
    "get_customer_cards": get_customer_cards,
    "block_card_and_order_replacement": block_card_and_order_replacement,
    "check_income_status": check_income_status,
}
