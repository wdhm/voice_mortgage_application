import pytest

from app.tools.actions import (
    PolicyError,
    block_card_and_order_replacement,
    book_meeting,
    offer_meeting_slots,
    request_consent,
    resolve_consent,
)


def test_card_action_requires_matching_explicit_consent(ready_case):
    credit_consent = request_consent(ready_case, "credit_check", ready_case.customer_profile.customer_id)
    resolve_consent(ready_case, credit_consent.consent_id, "Yes", granted=True)

    with pytest.raises(PolicyError, match="Matching explicit consent"):
        block_card_and_order_replacement(ready_case, "card-mastercard-4471", credit_consent.consent_id)

    assert ready_case.cards[0].status == "active"
    assert ready_case.replacement_order is None


def test_card_replacement_and_booking_are_idempotent(ready_case):
    card_consent = request_consent(
        ready_case,
        "block_card_and_order_replacement",
        "card-mastercard-4471",
    )
    resolve_consent(ready_case, card_consent.consent_id, "Yes, do that", granted=True)
    first_order = block_card_and_order_replacement(ready_case, "card-mastercard-4471", card_consent.consent_id)
    second_order = block_card_and_order_replacement(ready_case, "card-mastercard-4471", card_consent.consent_id)

    offer_meeting_slots(ready_case, after_three_weeks=True)
    first_booking = book_meeting(ready_case, "slot-20260921-1500")
    second_booking = book_meeting(ready_case, "slot-20260921-1500")

    assert first_order.order_reference == second_order.order_reference
    assert first_booking.booking_reference == second_booking.booking_reference
    card_events = [event for event in ready_case.events if event.display["label"] == "Block Mastercard 4471"]
    assert [event.event_type for event in card_events] == [
        "consent.requested",
        "consent.granted",
        "tool.completed",
    ]
    assert len([event for event in ready_case.events if event.display["label"] == "Book advisor meeting"]) == 1