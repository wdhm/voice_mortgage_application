from __future__ import annotations

import asyncio
import os
from typing import Literal

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI
from pydantic import BaseModel, Field

from app.domain.models import DemoCase, IdentityStatus
from app.tools.actions import (
    block_card_and_order_replacement,
    book_meeting,
    calculate_borrowing_capacity,
    offer_meeting_slots,
    request_consent,
    resolve_consent,
    run_credit_check,
    write_advisor_summary,
)

CustomerIntentName = Literal[
    "start_mortgage",
    "resolve_consent",
    "provide_deposit",
    "request_meeting",
    "book_meeting",
    "report_stolen_card",
    "other",
]


class CustomerIntent(BaseModel):
    intent: CustomerIntentName
    granted: bool | None = None
    deposit_sek: int | None = Field(default=None, ge=0)
    after_three_weeks: bool = False
    slot_id: str | None = None


def dispatch_intent(case: DemoCase, intent: CustomerIntent, transcript: str) -> str:
    active_consent = next((item for item in reversed(case.consents) if item.status == "requested"), None)
    if intent.intent == "resolve_consent" and active_consent and intent.granted is not None:
        resolve_consent(case, active_consent.consent_id, transcript, intent.granted)
        if not intent.granted:
            return "Understood. I will not take that action. We can continue with anything else."
        if active_consent.action == "credit_check":
            run_credit_check(case, active_consent.consent_id)
            return "The illustrative credit check is complete. What deposit will you use for the property?"
        block_card_and_order_replacement(case, active_consent.resource_scope, active_consent.consent_id)
        return "Mastercard ending 4471 is blocked and one replacement has been ordered for delivery in 5 to 7 business days."
    if case.identity_status != IdentityStatus.IDENTIFIED:
        return "Before we continue, please approve the DigitalD demo identity check on screen."
    if intent.intent == "start_mortgage":
        if case.accepted_income is None:
            return "I need a reviewed income document before I can continue with the preliminary mortgage assessment."
        request_consent(case, "credit_check", case.customer_profile.customer_id)
        return "May I run an illustrative credit check for this mortgage assessment? Please answer yes or no."
    if intent.intent == "provide_deposit" and intent.deposit_sek is not None and case.credit_result:
        case.deposit = intent.deposit_sek
        result = calculate_borrowing_capacity(case)
        write_advisor_summary(case)
        return (
            f"The preliminary assessment looks supportable, with an illustrative monthly surplus of "
            f"SEK {result.kalp_surplus_monthly:,}. An advisor still needs to make the final decision. "
            "Would you like to see meeting times?"
        )
    if intent.intent == "request_meeting":
        slots = offer_meeting_slots(case, after_three_weeks=intent.after_three_weeks)
        return "I can offer " + " or ".join(slot["label"] for slot in slots) + "."
    if intent.intent == "book_meeting" and intent.slot_id:
        meeting = book_meeting(case, intent.slot_id)
        return f"Your mock mortgage advisor meeting is booked for {meeting.starts_at:%d %B %Y at %H:%M}."
    if intent.intent == "report_stolen_card":
        card = case.cards[0]
        request_consent(case, "block_card_and_order_replacement", card.card_id)
        return "Should I block Mastercard ending 4471 and order a replacement now? Please answer yes or no."
    return "I can help with the mortgage application, advisor booking, or a stolen Bank Alfa card."


async def classify_customer_message(case: DemoCase, text: str) -> CustomerIntent:
    return await asyncio.to_thread(_classify_customer_message, case, text)


def _classify_customer_message(case: DemoCase, text: str) -> CustomerIntent:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    model = os.getenv("AZURE_OPENAI_MODEL", "gpt-5.2")
    if not endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured")
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
    try:
        client = OpenAI(base_url=f"{endpoint}/openai/v1/", api_key=token_provider)
        response = client.responses.parse(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Classify one Bank Alfa customer turn. Never infer consent unless the user explicitly "
                        "answers yes or no. Use a currently offered slot_id when booking. Return only the schema."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"State: identity={case.identity_status}, active_consent="
                        f"{next((item.action for item in reversed(case.consents) if item.status == 'requested'), None)}, "
                        f"offered_slots={case.offered_slot_ids}. Customer: {text}"
                    ),
                },
            ],
            text_format=CustomerIntent,
        )
        if response.output_parsed is None:
            raise RuntimeError("The intent model returned no structured result")
        return response.output_parsed
    finally:
        credential.close()