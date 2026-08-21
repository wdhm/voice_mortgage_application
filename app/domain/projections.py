from __future__ import annotations

from app.domain.models import DemoCase


def customer_projection(case: DemoCase) -> dict[str, object]:
    meeting = None
    if case.booked_meeting:
        meeting = {
            "starts_at": case.booked_meeting.starts_at.isoformat(),
            "ends_at": case.booked_meeting.ends_at.isoformat(),
            "timezone": case.booked_meeting.timezone,
            "booking_reference": case.booked_meeting.booking_reference,
        }
    blocked_card = next((card for card in case.cards if card.status == "blocked"), None)
    return {
        "customer_name": case.customer_profile.display_name,
        "identity_status": case.identity_status,
        "document": {
            "name": case.document_name,
            "status": case.document_status,
        },
        "transcript": case.transcript,
        "meeting": meeting,
        "card": (
            {
                "card_type": blocked_card.card_type,
                "last_four": blocked_card.last_four,
                "status": blocked_card.status,
                "replacement_ordered": case.replacement_order is not None,
            }
            if blocked_card
            else None
        ),
    }


def service_projection(case: DemoCase) -> dict[str, object]:
    return case.model_dump(mode="json")
