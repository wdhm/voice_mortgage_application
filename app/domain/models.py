"""Typed in-memory domain model for the Bank Alfa mortgage demo case.

This is the single source of truth for demo state. Tools (M2+) mutate it through
the repository; reset replaces it wholesale with the canonical Emma fixture and
bumps the case epoch so stale async callbacks can be discarded.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class IdentityStatus(str, Enum):
    unidentified = "unidentified"
    pending = "pending"
    identified = "identified"
    declined = "declined"


class DocumentState(str, Enum):
    empty = "empty"
    analyzing = "analyzing"
    accepted_automatically = "accepted_automatically"
    review_required = "review_required"
    accepted_after_review = "accepted_after_review"
    rejected_by_reviewer = "rejected_by_reviewer"
    analysis_failed = "analysis_failed"


class Provenance(str, Enum):
    extracted = "extracted"
    human_approved = "human-approved"


class ConsentAction(str, Enum):
    credit_check = "credit_check"
    block_card = "block_card_and_order_replacement"


class ConsentStatus(str, Enum):
    requested = "requested"
    granted = "granted"
    denied = "denied"
    expired = "expired"
    consumed = "consumed"


class CaseOutcome(str, Enum):
    open = "open"
    preliminary_positive = "preliminary_positive"
    preliminary_negative = "preliminary_negative"
    insufficient_information = "insufficient_information"


class CardStatus(str, Enum):
    active = "active"
    blocked = "blocked"


# --------------------------------------------------------------------------- #
# Sub-models
# --------------------------------------------------------------------------- #
class CustomerProfile(BaseModel):
    customer_id: str
    customer_number: str
    display_name: str
    phone_number: str
    email: str
    street_address: str
    postal_code: str
    city: str
    country: str
    preferred_language: str = "English"
    customer_since: date
    contact_details_updated_at: datetime | None = None
    contact_details_updated_by: str | None = None
    employer_name: str | None = None
    relationship_summary: str | None = None
    existing_car_loan_balance: int | None = None  # SEK
    existing_car_loan_payment: int | None = None  # SEK / month


class IncomeField(BaseModel):
    """One extracted field with value, confidence and provenance."""
    name: str
    value: str | None = None
    normalized_value: float | str | None = None
    confidence: float | None = None
    provenance: Provenance = Provenance.extracted
    source_grounding: str | None = None
    original_value: str | None = None  # retained when a human edits it


class ExtractedIncome(BaseModel):
    employer_name: IncomeField
    gross_salary_monthly: IncomeField
    net_salary_monthly: IncomeField
    employment_type: IncomeField
    pay_date: IncomeField


class AcceptedIncome(BaseModel):
    employer_name: str
    gross_salary_monthly: int
    net_salary_monthly: int
    employment_type: str
    pay_date: date
    provenance: Provenance
    accepted_at: datetime


class ReviewRecord(BaseModel):
    reviewer: str = "demo-reviewer"
    edited_fields: list[str] = Field(default_factory=list)
    decision: str | None = None  # approved | rejected
    resolved_at: datetime | None = None


class UploadedDocument(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sample_key: str | None = None  # "high_confidence" | "low_confidence" | None
    uploaded_at: datetime
    # Analyzer provenance (for the advisor's structured extraction export).
    analyzer_provider: str | None = None  # "simulated" | "foundry"
    analyzer_id: str | None = None
    analyzer_method: str | None = None


class PropertyRequest(BaseModel):
    location: str
    purchase_price: int
    deposit: int | None = None


class CreditResult(BaseModel):
    score: int
    max_score: int
    risk_band: str
    existing_debt_balance: int
    existing_debt_payment: int
    defaults: str
    source: str
    checked_at: datetime


class ConsentRecord(BaseModel):
    consent_id: str
    session_id: str
    customer_id: str | None = None
    action: ConsentAction
    resource_scope: str | None = None  # e.g. card id for block_card
    status: ConsentStatus = ConsentStatus.requested
    final_user_transcript: str | None = None
    requested_at: datetime
    resolved_at: datetime | None = None


class CapacityResult(BaseModel):
    inputs: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    outcome: CaseOutcome = CaseOutcome.open
    assumptions: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    calculated_at: datetime


class MeetingSlot(BaseModel):
    slot_id: str
    start: datetime
    end: datetime
    timezone: str = "Europe/Stockholm"
    advisor: str = "Mortgage advisor"


class BookedMeeting(BaseModel):
    slot: MeetingSlot
    purpose: str
    booking_reference: str
    booked_at: datetime


class Card(BaseModel):
    card_id: str
    card_type: str
    last_four: str
    status: CardStatus = CardStatus.active


class ReplacementOrder(BaseModel):
    order_reference: str
    card_id: str
    reason: str
    delivery_estimate: str
    ordered_at: datetime


class AdvisorSummary(BaseModel):
    sections: dict = Field(default_factory=dict)
    summary: str = ""
    flags: list[str] = Field(default_factory=list)
    recommended_action: str = "standard_review"
    final_decision_required: bool = True
    status_text: str = "Preliminary assessment: looks supportable"
    decision_text: str = "Final decision: advisor required"
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Aggregate root
# --------------------------------------------------------------------------- #
class DemoCase(BaseModel):
    case_id: str
    session_id: str
    epoch: int = 0  # bumped on every reset; stale async callbacks are discarded

    customer_profile: CustomerProfile
    identity_status: IdentityStatus = IdentityStatus.unidentified

    uploaded_document: UploadedDocument | None = None
    document_state: DocumentState = DocumentState.empty
    extracted_income: ExtractedIncome | None = None
    accepted_income: AcceptedIncome | None = None
    review_record: ReviewRecord | None = None

    property_request: PropertyRequest | None = None
    credit_result: CreditResult | None = None
    consent_records: list[ConsentRecord] = Field(default_factory=list)
    capacity_result: CapacityResult | None = None
    advisor_summary: AdvisorSummary | None = None

    offered_meeting_slots: list[MeetingSlot] = Field(default_factory=list)
    booked_meeting: BookedMeeting | None = None

    cards: list[Card] = Field(default_factory=list)
    replacement_order: ReplacementOrder | None = None

    outcome: CaseOutcome = CaseOutcome.open
