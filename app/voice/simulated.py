"""Simulated-text conversation provider: a deterministic scripted agent.

This is the recorded-demo path. It reproduces the 20 behavioural beats of the
script exactly and repeatably, WITHOUT any Azure dependency, while still going
through the real governed host — so consent gates, guards, and golden numbers
are genuine, not faked. The agent advances through explicit phases; protected
actions are only attempted after the host has resolved the customer's real
affirmative turn, so the credit-check and card-block consent gates are exercised
for real even in simulation.
"""
from __future__ import annotations

import re
from enum import Enum, auto

from ..domain.fixtures import MASTERCARD_ID
from .port import ConversationHost

# Canonical demo figures (business-case-and-demo-script.md) — pinned so the
# borrowing-capacity golden numbers are identical on every recording.
PROPERTY_PRICE = 7_000_000
DEPOSIT = 1_750_000
NEAR_DATE = "2026-08-24"       # first availability window
RESCHEDULE_DATE = "2026-09-21"  # after Emma's three weeks away
CANONICAL_SLOT = "slot-2026-09-21-1500"  # Monday 21 September 2026, 15:00


class Phase(Enum):
    AWAIT_MORTGAGE = auto()
    AWAIT_PHONE_NUMBER = auto()
    AWAIT_PHONE_CONFIRMATION = auto()
    AWAIT_CREDIT_CONSENT = auto()
    AWAIT_DEPOSIT = auto()
    AWAIT_MEETING = auto()
    AWAIT_RESCHEDULE = auto()
    AWAIT_CARD = auto()
    DONE = auto()


def _mentions_reschedule(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("away", "week", "after that", "later", "another time"))


def _mentions_phone_update(text: str) -> bool:
    lowered = text.lower()
    return "phone" in lowered or "mobile" in lowered or "telephone" in lowered


def _mentions_payslip_help(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("payslip", "pay slip", "salary slip", "income document", "income verification")
    )


def _extract_phone_number(text: str) -> str | None:
    match = re.search(r"(?:\+46|0046|0)(?:[\s().-]*\d){7,10}", text)
    return match.group(0).strip() if match else None


def _is_affirmative(text: str) -> bool:
    lowered = text.strip().lower()
    return any(word in lowered for word in ("yes", "correct", "confirm", "that's right", "go ahead"))


class SimulatedVoiceSession:
    provider = "simulated"

    def __init__(self, host: ConversationHost) -> None:
        self._host = host
        self._phase = Phase.AWAIT_MORTGAGE
        self._phone_candidate: str | None = None
        self._return_phase = Phase.AWAIT_MORTGAGE

    async def start(self) -> None:
        profile = await self._host.call_tool("get_crm_profile")
        await self._host.say(
            f"Welcome to Bank Alfa, Emma. {profile.summary} How can I help you today?"
        )
        self._phase = Phase.AWAIT_MORTGAGE

    async def on_user_audio(self, pcm_b64: str) -> None:  # simulated path is text-only
        return

    async def on_user_audio_commit(self) -> None:
        return

    async def barge_in(self) -> None:
        await self._host.push({"type": "agent_interrupted"})

    async def close(self) -> None:
        return

    async def on_user_text(self, text: str) -> None:
        # Echo the customer's turn AND resolve any pending consent server-side first.
        await self._host.user_said(text)
        if _mentions_payslip_help(text):
            await self._handle_payslip_help()
            return
        if _mentions_phone_update(text) and self._phase not in {
            Phase.AWAIT_PHONE_NUMBER,
            Phase.AWAIT_PHONE_CONFIRMATION,
        }:
            self._return_phase = self._phase
            await self._begin_phone_update(text)
            return
        handler = {
            Phase.AWAIT_MORTGAGE: self._on_mortgage,
            Phase.AWAIT_PHONE_NUMBER: self._on_phone_number,
            Phase.AWAIT_PHONE_CONFIRMATION: self._on_phone_confirmation,
            Phase.AWAIT_CREDIT_CONSENT: self._on_credit_consent,
            Phase.AWAIT_DEPOSIT: self._on_deposit,
            Phase.AWAIT_MEETING: self._on_meeting,
            Phase.AWAIT_RESCHEDULE: self._on_reschedule,
            Phase.AWAIT_CARD: self._on_card,
            Phase.DONE: self._on_done,
        }[self._phase]
        await handler(text)

    # ---- phase handlers -------------------------------------------------- #
    async def _handle_payslip_help(self) -> None:
        status = await self._host.call_tool("check_income_status")
        state = status.result.get("document_state")
        if status.result.get("income_verified"):
            await self._host.say(
                "Your payslip has now been approved and your income is verified. "
                "The only step left for you is to book an appointment with a mortgage advisor. "
                "Would you like me to find an available time?"
            )
        elif state == "review_required":
            await self._host.say(
                "The new payslip was read successfully and passed the automated checks. "
                "It is now waiting for a Bank Alfa advisor to approve it."
            )
        elif state == "empty":
            await self._host.say(
                "Please upload a clear copy of your latest payslip in Income verification. "
                "You can do that while we are on the call."
            )
        else:
            await self._host.say(
                "I'm sorry, the scan is too blurry for us to read the income details. "
                "Please remove it and upload a clearer copy in Income verification. "
                "You can do that while we are on the call."
            )

    async def _begin_phone_update(self, text: str) -> None:
        candidate = _extract_phone_number(text)
        if candidate:
            self._phone_candidate = candidate
            await self._host.say(
                f"I heard your new phone number as {candidate}. Is that correct?"
            )
            self._phase = Phase.AWAIT_PHONE_CONFIRMATION
            return
        await self._host.say("Of course. What is the new phone number you would like to register?")
        self._phase = Phase.AWAIT_PHONE_NUMBER

    async def _on_phone_number(self, text: str) -> None:
        candidate = _extract_phone_number(text)
        if not candidate:
            await self._host.say(
                "I didn't catch a complete Swedish phone number. Please say the full number again."
            )
            return
        self._phone_candidate = candidate
        await self._host.say(f"I heard {candidate}. Is that the number you want me to save?")
        self._phase = Phase.AWAIT_PHONE_CONFIRMATION

    async def _on_phone_confirmation(self, text: str) -> None:
        if not _is_affirmative(text):
            self._phone_candidate = None
            await self._host.say("No problem. Please tell me the phone number again.")
            self._phase = Phase.AWAIT_PHONE_NUMBER
            return
        out = await self._host.call_tool(
            "update_customer_phone_number", {"phone_number": self._phone_candidate}
        )
        if out.ok:
            await self._host.say(
                f"Done. {out.summary} You can see the updated number in Personal information."
            )
            self._phase = self._return_phase
            return
        await self._host.say(f"I couldn't update it. {out.summary} Please say the number again.")
        self._phase = Phase.AWAIT_PHONE_NUMBER

    async def _on_mortgage(self, text: str) -> None:
        await self._host.say(
            "Great — a mortgage pre-approval for Täby. Good news: your income is already "
            "verified from your payslip, so I won't ask for that again. Before I check your "
            "credit, may I run a credit check with the bureau?"
        )
        await self._host.request_consent("credit_check")
        self._phase = Phase.AWAIT_CREDIT_CONSENT

    async def _on_credit_consent(self, text: str) -> None:
        out = await self._host.call_tool("run_credit_check")
        if not out.ok:
            await self._host.say(
                "No problem — I won't run it without your go-ahead. Just to confirm, may I run the credit check?"
            )
            await self._host.request_consent("credit_check")
            return
        await self._host.say(
            "Thanks. Your credit check came back strong. To estimate what you can borrow, "
            "how much do you have available as a deposit?"
        )
        self._phase = Phase.AWAIT_DEPOSIT

    async def _on_deposit(self, text: str) -> None:
        cap = await self._host.call_tool(
            "calculate_borrowing_capacity",
            {"purchasePrice": PROPERTY_PRICE, "deposit": DEPOSIT, "location": "Täby"},
        )
        if cap.ok:
            result = cap.result
            remaining = result["netAfterStress"]
            if result["verdict"] == "not_affordable_at_stress_rate":
                message = (
                    f"At the 7 percent stress rate, the monthly budget would be short by "
                    f"about {abs(remaining):,} kronor."
                )
            else:
                message = (
                    f"At the 7 percent stress rate, the monthly budget remains positive "
                    f"by about {remaining:,} kronor."
                )
            if result["dtiFlag"] == "above_soft_guideline":
                message += (
                    f" Your debt-to-income ratio is {result['dtiRatio']} times, which is "
                    "above the 4.5 times soft guideline, so I will note that for the advisor."
                )
            message += (
                " This is preliminary, and a human advisor makes the final decision."
            )
            await self._host.say(message)
        await self._host.call_tool("write_advisor_summary")
        await self._host.say(
            "Your assessment is ready for bank review. After you review it, continue to "
            "the appointment step and tell me when you are available."
        )
        slots = await self._host.call_tool("get_available_meeting_times", {"earliest_date": NEAR_DATE})
        if slots.ok:
            await self._host.say("Here are some near-term options: " + slots.summary)
        self._phase = Phase.AWAIT_MEETING

    async def _on_meeting(self, text: str) -> None:
        if _mentions_reschedule(text):
            later = await self._host.call_tool(
                "get_available_meeting_times", {"earliest_date": RESCHEDULE_DATE}
            )
            await self._host.say(
                "Of course — after your three weeks away, here's what's open: "
                + (later.summary if later.ok else "")
            )
            self._phase = Phase.AWAIT_RESCHEDULE
        else:
            await self._book(text)

    async def _on_reschedule(self, text: str) -> None:
        await self._book(text)

    async def _book(self, text: str) -> None:
        booked = await self._host.call_tool(
            "book_meeting", {"slot_id": CANONICAL_SLOT, "purpose": "Mortgage advisory meeting"}
        )
        if booked.ok:
            await self._host.say(
                "You're booked with a mortgage advisor on Monday 21 September at 15:00. "
                "Your part of the application is now complete. The advisor will review your "
                "application and make the final lending decision at the appointment."
            )
            self._phase = Phase.AWAIT_CARD
        else:
            await self._host.say("That time didn't work — could you pick one of the offered slots again?")

    async def _on_card(self, text: str) -> None:
        await self._host.call_tool("get_customer_cards")
        out = await self._host.call_tool(
            "block_card_and_order_replacement", {"card_id": MASTERCARD_ID, "reason": "stolen"}
        )
        if not out.ok:
            await self._host.say(
                "I couldn't block Mastercard ending 4471. Please try again or contact card support."
            )
            return
        await self._host.say(
            "I found your Bank Alfa Mastercard ending 4471. It is now blocked and a replacement is on its way. "
            "To recap: your credit check is complete, your preliminary mortgage numbers look supportable "
            "pending an advisor's final decision, and you're booked for Monday 21 September at 15:00. "
            "Take care, Emma — goodbye."
        )
        self._phase = Phase.DONE

    async def _on_done(self, text: str) -> None:
        await self._host.say("We're all set for today. Thanks for banking with Bank Alfa — goodbye.")
