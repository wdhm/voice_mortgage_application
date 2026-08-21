from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.models import (
    AcceptedIncome,
    CapacityResult,
    ConsentRecord,
    ConsentStatus,
    CreditResult,
    DemoCase,
    Meeting,
    ReplacementOrder,
    utc_now,
)
from app.realtime.events import add_event


class PolicyError(ValueError):
    pass


def request_consent(case: DemoCase, action: str, resource_scope: str) -> ConsentRecord:
    consent = ConsentRecord(
        consent_id=f"consent-{len(case.consents) + 1:03d}",
        session_id=case.session_id,
        customer_id=case.customer_profile.customer_id,
        action=action,  # type: ignore[arg-type]
        resource_scope=resource_scope,
    )
    case.consents.append(consent)
    add_event(case, "consent.requested", consent_label(action), "queued", "Policy guard")
    return consent


def resolve_consent(case: DemoCase, consent_id: str, transcript: str, granted: bool) -> ConsentRecord:
    consent = next((item for item in case.consents if item.consent_id == consent_id), None)
    if consent is None or consent.status != ConsentStatus.REQUESTED:
        raise PolicyError("Consent request is not active")
    consent.status = ConsentStatus.GRANTED if granted else ConsentStatus.DENIED
    consent.final_user_transcript = transcript
    consent.resolved_at = utc_now()
    add_event(
        case,
        f"consent.{'granted' if granted else 'denied'}",
        consent_label(consent.action),
        "completed" if granted else "blocked",
        "Policy guard",
    )
    return consent


def run_credit_check(case: DemoCase, consent_id: str) -> CreditResult:
    consent = require_consent(case, consent_id, "credit_check", case.customer_profile.customer_id)
    result = CreditResult(
        score=781,
        risk_band="low",
        existing_debt_balance=180_000,
        monthly_payment=4_200,
        defaults="none",
    )
    case.credit_result = result
    consume_consent(consent)
    add_event(case, "tool.completed", "Run credit check", "completed", "Mock credit bureau")
    return result


def calculate_borrowing_capacity(case: DemoCase) -> CapacityResult:
    if case.accepted_income is None or case.credit_result is None:
        raise PolicyError("Accepted income and credit result are required")
    income = case.accepted_income
    mortgage = case.property_price - case.deposit
    total_debt = mortgage + case.credit_result.existing_debt_balance
    annual_income = income.gross_salary_monthly * 12
    base_amortization = round(mortgage * 0.02 / 12)
    additional_amortization = round(mortgage * 0.01 / 12) if total_debt / annual_income > 4.5 else 0
    gross_interest = round(mortgage * 0.07 / 12)
    tax_adjustment = round(gross_interest * 0.30)
    net_interest = gross_interest - tax_adjustment
    surplus = (
        income.net_salary_monthly
        - base_amortization
        - additional_amortization
        - net_interest
        - 12_500
        - 6_000
        - case.credit_result.monthly_payment
    )
    result = CapacityResult(
        property_price=case.property_price,
        deposit=case.deposit,
        requested_mortgage=mortgage,
        ltv=round(mortgage / case.property_price, 4),
        total_debt=total_debt,
        annual_gross_income=annual_income,
        debt_ratio=round(total_debt / annual_income, 2),
        base_amortization_monthly=base_amortization,
        additional_amortization_monthly=additional_amortization,
        total_amortization_monthly=base_amortization + additional_amortization,
        stressed_interest_rate=0.07,
        stressed_gross_interest_monthly=gross_interest,
        illustrative_tax_adjustment_monthly=tax_adjustment,
        stressed_net_interest_monthly=net_interest,
        living_cost_monthly=12_500,
        property_running_cost_monthly=6_000,
        existing_debt_payment_monthly=case.credit_result.monthly_payment,
        kalp_surplus_monthly=surplus,
        outcome="preliminary_positive" if surplus > 0 else "preliminary_negative",
        assumptions=[
            "7% stressed interest rate",
            "30% illustrative interest tax adjustment",
            "SEK 12,500 household living cost",
            "SEK 6,000 property running cost",
            "Illustrative demo policy, not financial advice",
        ],
    )
    case.capacity_result = result
    add_event(case, "tool.completed", "Calculate borrowing capacity", "completed", "Mock mortgage engine")
    add_event(case, "handoff.required", "Advisor final decision", "review", "Bank Alfa")
    return result


def write_advisor_summary(case: DemoCase) -> dict[str, object]:
    if not all((case.accepted_income, case.credit_result, case.capacity_result)):
        raise PolicyError("Verified income, credit, and capacity are required")
    case.advisor_summary = {
        "identity": "DigitalD demo identification complete",
        "income_provenance": case.accepted_income.provenance,
        "requested_mortgage": case.capacity_result.requested_mortgage,
        "credit_risk_band": case.credit_result.risk_band,
        "capacity_metrics": {
            "ltv": case.capacity_result.ltv,
            "debt_ratio": case.capacity_result.debt_ratio,
            "kalp_surplus_monthly": case.capacity_result.kalp_surplus_monthly,
        },
        "risks_and_caveats": case.capacity_result.assumptions,
        "final_decision_required": True,
    }
    add_event(case, "tool.completed", "Write advisor summary", "completed", "Mock CRM")
    return case.advisor_summary


def offer_meeting_slots(case: DemoCase, after_three_weeks: bool) -> list[dict[str, str]]:
    if after_three_weeks:
        slots = [{"slot_id": "slot-20260921-1500", "label": "21 September 2026 at 15:00"}]
    else:
        slots = [
            {"slot_id": "slot-20260903-1000", "label": "3 September 2026 at 10:00"},
            {"slot_id": "slot-20260904-1400", "label": "4 September 2026 at 14:00"},
        ]
    case.offered_slot_ids = [slot["slot_id"] for slot in slots]
    add_event(case, "tool.completed", "Get available meeting times", "completed", "Mock calendar")
    return slots


def book_meeting(case: DemoCase, slot_id: str) -> Meeting:
    if case.booked_meeting and case.booked_meeting.slot_id == slot_id:
        return case.booked_meeting
    if slot_id not in case.offered_slot_ids:
        raise PolicyError("Meeting slot was not offered in this session")
    if slot_id != "slot-20260921-1500":
        raise PolicyError("Starter demo books the canonical later appointment")
    starts_at = datetime(2026, 9, 21, 15, 0, tzinfo=ZoneInfo("Europe/Stockholm"))
    case.booked_meeting = Meeting(
        slot_id=slot_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=45),
        booking_reference="BA-MTG-210926-1500",
    )
    add_event(case, "tool.completed", "Book advisor meeting", "completed", "Mock calendar")
    return case.booked_meeting


def block_card_and_order_replacement(case: DemoCase, card_id: str, consent_id: str) -> ReplacementOrder:
    if case.replacement_order and case.replacement_order.card_id == card_id:
        return case.replacement_order
    require_consent(case, consent_id, "block_card_and_order_replacement", card_id)
    card = next((item for item in case.cards if item.card_id == card_id), None)
    if card is None:
        raise PolicyError("Card not found")
    card.status = "blocked"
    card.blocked_at = utc_now()
    case.replacement_order = ReplacementOrder(
        order_reference="BA-CARD-4471-REPLACE",
        card_id=card_id,
        delivery_estimate="5-7 business days",
    )
    consent = next(item for item in case.consents if item.consent_id == consent_id)
    consume_consent(consent)
    add_event(case, "tool.completed", "Block Mastercard 4471", "completed", "Mock Cards")
    return case.replacement_order


def accept_extracted_income(case: DemoCase, provenance: str) -> AcceptedIncome:
    if case.extracted_income is None:
        raise PolicyError("No extraction is available")
    fields = case.extracted_income
    income = AcceptedIncome(
        employer_name=str(fields.employer_name.value),
        gross_salary_monthly=int(fields.gross_salary_monthly.value or 0),
        net_salary_monthly=int(fields.net_salary_monthly.value or 0),
        employment_type=str(fields.employment_type.value),
        pay_date=fields.pay_date.value,  # type: ignore[arg-type]
        provenance=provenance,
    )
    case.accepted_income = income
    return income


def require_consent(case: DemoCase, consent_id: str, action: str, scope: str) -> ConsentRecord:
    consent = next((item for item in case.consents if item.consent_id == consent_id), None)
    valid = (
        consent is not None
        and consent.session_id == case.session_id
        and consent.customer_id == case.customer_profile.customer_id
        and consent.action == action
        and consent.resource_scope == scope
        and consent.status == ConsentStatus.GRANTED
    )
    if not valid:
        add_event(case, "tool.blocked_by_policy", consent_label(action), "blocked", "Policy guard")
        raise PolicyError("Matching explicit consent is required")
    return consent


def consume_consent(consent: ConsentRecord) -> None:
    consent.status = ConsentStatus.CONSUMED
    consent.resolved_at = utc_now()


def consent_label(action: str) -> str:
    return "Credit check" if action == "credit_check" else "Block Mastercard 4471"