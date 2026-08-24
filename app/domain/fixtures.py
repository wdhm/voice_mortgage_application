"""Canonical Emma Lindberg fixture — the starting state after every reset.

All values are fictional demo data (per docs/business-case-and-demo-script.md).
The customer record exists, but no income is accepted, no identity is confirmed,
and both cards are active with no replacement order.
"""
from __future__ import annotations

from datetime import UTC, date

from .models import (
    AcceptedIncome,
    Card,
    CardStatus,
    CustomerProfile,
    DemoCase,
    DocumentState,
    IdentityStatus,
    Provenance,
)

# Canonical identifiers kept stable so tools and the UI can reference them.
CASE_ID = "case-emma"
CUSTOMER_ID = "cust-emma-lindberg"
MASTERCARD_ID = "card-mc-4471"
VISA_DEBIT_ID = "card-visa-1842"


def build_canonical_case(session_id: str, epoch: int = 0) -> DemoCase:
    """Return a fresh canonical DemoCase for the given session and epoch."""
    return DemoCase(
        case_id=CASE_ID,
        session_id=session_id,
        epoch=epoch,
        identity_status=IdentityStatus.identified,
        document_state=DocumentState.empty,
        customer_profile=CustomerProfile(
            customer_id=CUSTOMER_ID,
            customer_number="1048 572 963",
            display_name="Emma Lindberg",
            phone_number="+46 70 123 45 67",
            email="emma.lindberg@example.com",
            street_address="Parkvägen 12",
            postal_code="183 34",
            city="Täby",
            country="Sweden",
            preferred_language="English",
            customer_since=date(2018, 4, 12),
            employer_name="Northstar AB",
            relationship_summary="Existing Bank Alfa customer with an active car loan.",
            existing_car_loan_balance=180_000,
            existing_car_loan_payment=4_200,
        ),
        cards=[
            Card(
                card_id=MASTERCARD_ID,
                card_type="Bank Alfa Mastercard",
                last_four="4471",
                status=CardStatus.active,
            ),
            Card(
                card_id=VISA_DEBIT_ID,
                card_type="Bank Alfa Everyday Debit",
                last_four="1842",
                status=CardStatus.active,
            ),
        ],
    )


# Canonical accepted-income values Emma's high-confidence payslip yields. The M3
# document flow will produce this for real; until then tools/tests seed it here
# so Part 2 (mortgage capacity) is exercisable without the document pipeline.
def apply_accepted_income_emma(case: DemoCase) -> DemoCase:
    from datetime import date, datetime

    case.accepted_income = AcceptedIncome(
        employer_name="Northstar AB",
        gross_salary_monthly=96_000,
        net_salary_monthly=62_400,
        employment_type="permanent",
        pay_date=date(2026, 8, 25),
        provenance=Provenance.extracted,
        accepted_at=datetime.now(UTC),
    )
    case.document_state = DocumentState.accepted_automatically
    return case
