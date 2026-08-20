"""Typed in-memory domain model for the Bank Alfa mortgage demo case.

This is the single source of truth for demo state. Tools (M2+) mutate it through
the repository; reset replaces it wholesale with the canonical Emma fixture and
bumps the case epoch so stale async callbacks can be discarded.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

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
    display_name: str
    employer_name: Optional[str] = None
    relationship_summary: Optional[str] = None
    existing_car_loan_balance: Optional[int] = None  # SEK
    existing_car_loan_payment: Optional[int] = None  # SEK / month


class IncomeField(BaseModel):
    """One extracted field with value, confidence and provenance."""
    name: str
    value: Optional[str] = None
    normalized_value: Optional[float | str] = None
    confidence: Optional[float] = None
    provenance: Provenance = Provenance.extracted
    source_grounding: Optional[str] = None
    original_value: Optional[str] = None  # retained when a human edits it


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
    decision: Optional[str] = None  # approved | rejected
    resolved_at: Optional[datetime] = None


class UploadedDocument(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sample_key: Optional[str] = None  # "high_confidence" | "low_confidence" | None
    uploaded_at: datetime


class PropertyRequest(BaseModel):
    location: str
    purchase_price: int
    deposit: Optional[int] = None


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
    customer_id: Optional[str] = None
    action: ConsentAction
    resource_scope: Optional[str] = None  # e.g. card id for block_card
    status: ConsentStatus = ConsentStatus.requested
    final_user_transcript: Optional[str] = None
    requested_at: datetime
    resolved_at: Optional[datetime] = None


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

    uploaded_document: Optional[UploadedDocument] = None
    document_state: DocumentState = DocumentState.empty
    extracted_income: Optional[ExtractedIncome] = None
    accepted_income: Optional[AcceptedIncome] = None
    review_record: Optional[ReviewRecord] = None

    property_request: Optional[PropertyRequest] = None
    credit_result: Optional[CreditResult] = None
    consent_records: list[ConsentRecord] = Field(default_factory=list)
    capacity_result: Optional[CapacityResult] = None
    advisor_summary: Optional[AdvisorSummary] = None

    offered_meeting_slots: list[MeetingSlot] = Field(default_factory=list)
    booked_meeting: Optional[BookedMeeting] = None

    cards: list[Card] = Field(default_factory=list)
    replacement_order: Optional[ReplacementOrder] = None

    outcome: CaseOutcome = CaseOutcome.open
