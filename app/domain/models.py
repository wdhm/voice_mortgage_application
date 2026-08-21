from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentStatus(StrEnum):
    NOT_UPLOADED = "not_uploaded"
    ACCEPTED_AUTOMATICALLY = "accepted_automatically"
    REVIEW_REQUIRED = "review_required"
    ACCEPTED_AFTER_REVIEW = "accepted_after_review"
    REJECTED_BY_REVIEWER = "rejected_by_reviewer"
    ANALYSIS_FAILED = "analysis_failed"


class IdentityStatus(StrEnum):
    NOT_IDENTIFIED = "not_identified"
    IDENTIFIED = "identified"
    DECLINED = "declined"


class ConsentStatus(StrEnum):
    REQUESTED = "requested"
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ExtractedField(BaseModel):
    value: str | int | float | date | None
    confidence: float | None = Field(default=None, ge=0, le=1)
    grounding: str | None = None
    method: str = "demo_adapter"
    provenance: str = "ai-extracted"
    original_value: str | int | float | date | None = None


class ExtractedIncome(BaseModel):
    employer_name: ExtractedField
    gross_salary_monthly: ExtractedField
    net_salary_monthly: ExtractedField
    employment_type: ExtractedField
    pay_date: ExtractedField


class AcceptedIncome(BaseModel):
    employer_name: str
    gross_salary_monthly: int
    net_salary_monthly: int
    employment_type: str
    pay_date: date
    provenance: str
    accepted_at: datetime = Field(default_factory=utc_now)


class CustomerProfile(BaseModel):
    customer_id: str
    display_name: str
    city: str
    relationship_since: int
    contact_summary: str
    car_loan_balance: int
    car_loan_payment: int


class CreditResult(BaseModel):
    score: int
    maximum_score: int = 999
    risk_band: str
    existing_debt_balance: int
    monthly_payment: int
    defaults: str
    source: str = "mock_credit_bureau"


class CapacityResult(BaseModel):
    property_price: int
    deposit: int
    requested_mortgage: int
    ltv: float
    total_debt: int
    annual_gross_income: int
    debt_ratio: float
    base_amortization_monthly: int
    additional_amortization_monthly: int
    total_amortization_monthly: int
    stressed_interest_rate: float
    stressed_gross_interest_monthly: int
    illustrative_tax_adjustment_monthly: int
    stressed_net_interest_monthly: int
    living_cost_monthly: int
    property_running_cost_monthly: int
    existing_debt_payment_monthly: int
    kalp_surplus_monthly: int
    outcome: Literal["preliminary_positive", "preliminary_negative"]
    assumptions: list[str]
    advisor_decision_required: bool = True


class ConsentRecord(BaseModel):
    consent_id: str
    session_id: str
    customer_id: str
    action: Literal["credit_check", "block_card_and_order_replacement"]
    resource_scope: str
    status: ConsentStatus = ConsentStatus.REQUESTED
    final_user_transcript: str | None = None
    requested_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None


class Meeting(BaseModel):
    slot_id: str
    starts_at: datetime
    ends_at: datetime
    timezone: str = "Europe/Stockholm"
    advisor_type: str = "mortgage_advisor"
    booking_reference: str


class Card(BaseModel):
    card_id: str
    card_type: str
    last_four: str
    status: Literal["active", "blocked"] = "active"
    blocked_at: datetime | None = None


class ReplacementOrder(BaseModel):
    order_reference: str
    card_id: str
    delivery_estimate: str
    ordered_at: datetime = Field(default_factory=utc_now)


class ActivityEvent(BaseModel):
    event_id: str
    event_type: str
    session_id: str
    case_id: str
    correlation_id: str
    sequence: int
    timestamp: datetime = Field(default_factory=utc_now)
    display: dict[str, str]


class DemoCase(BaseModel):
    case_id: str
    session_id: str
    customer_profile: CustomerProfile
    identity_status: IdentityStatus = IdentityStatus.NOT_IDENTIFIED
    document_name: str | None = None
    document_status: DocumentStatus = DocumentStatus.NOT_UPLOADED
    extracted_income: ExtractedIncome | None = None
    accepted_income: AcceptedIncome | None = None
    review_notes: str | None = None
    property_location: str = "Täby"
    property_price: int = 7_000_000
    deposit: int = 1_750_000
    credit_result: CreditResult | None = None
    consents: list[ConsentRecord] = Field(default_factory=list)
    capacity_result: CapacityResult | None = None
    advisor_summary: dict[str, Any] | None = None
    offered_slot_ids: list[str] = Field(default_factory=list)
    booked_meeting: Meeting | None = None
    cards: list[Card]
    replacement_order: ReplacementOrder | None = None
    transcript: list[dict[str, str]] = Field(default_factory=list)
    events: list[ActivityEvent] = Field(default_factory=list)
