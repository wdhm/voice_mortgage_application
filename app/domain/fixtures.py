"""Canonical Emma Lindberg fixture — the starting state after every reset.

All values are fictional demo data (per docs/business-case-and-demo-script.md).
The customer record exists, but no income is accepted, no identity is confirmed,
and Mastercard ending 4471 is active with no replacement order.
"""
from __future__ import annotations

from .models import (
    Card,
    CardStatus,
    CustomerProfile,
    DemoCase,
    DocumentState,
    IdentityStatus,
)

# Canonical identifiers kept stable so tools and the UI can reference them.
CASE_ID = "case-emma"
CUSTOMER_ID = "cust-emma-lindberg"
MASTERCARD_ID = "card-mc-4471"


def build_canonical_case(session_id: str, epoch: int = 0) -> DemoCase:
    """Return a fresh canonical DemoCase for the given session and epoch."""
    return DemoCase(
        case_id=CASE_ID,
        session_id=session_id,
        epoch=epoch,
        identity_status=IdentityStatus.unidentified,
        document_state=DocumentState.empty,
        customer_profile=CustomerProfile(
            customer_id=CUSTOMER_ID,
            display_name="Emma Lindberg",
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
        ],
    )
