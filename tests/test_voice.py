"""Voice orchestration: the simulated scripted agent runs the full 20-beat script
through the governed host, proving consent gates and golden numbers over the same
path the real Voice Live provider will use.
"""
from __future__ import annotations

import pytest

from app.domain.consent import ConsentEngine
from app.domain.fixtures import CASE_ID
from app.domain.models import CardStatus, IdentityStatus
from app.domain.repository import InMemoryCaseRepository
from app.events.bus import EventBus
from app.tools.dispatcher import ToolDispatcher
from app.voice.host import VoiceOrchestrator


class VoiceHarness:
    def __init__(self) -> None:
        self.repo = InMemoryCaseRepository(session_id="session-test")
        self.bus = EventBus(session_id="session-test", case_id=CASE_ID)
        self.bus.set_epoch(self.repo.epoch)
        self.tools = ToolDispatcher(self.repo, self.bus, ConsentEngine())
        self.orch = VoiceOrchestrator(self.repo, self.bus, self.tools, "simulated")
        self.q = self.orch.channel.subscribe()

    def drain(self) -> list[dict]:
        msgs = []
        while not self.q.empty():
            msgs.append(self.q.get_nowait())
        return msgs

    async def run_to_completion(self, seed_income: bool = True):
        if seed_income:
            from app.domain.fixtures import apply_accepted_income_emma

            case = self.repo.get()
            apply_accepted_income_emma(case)
            self.repo.set(case)
        self._all: list[dict] = []
        await self.orch.start()
        beats = [
            "I want a mortgage pre-approval for a house in Täby, around seven million kronor.",
            "Yes, you can run the credit check.",
            "I have one million seven hundred and fifty thousand kronor.",
            "I'm away for three weeks. Do you have anything after that?",
            "Monday the 21st of September at 15:00 works.",
            "One more thing — my card was stolen. Please block it.",
        ]
        for b in beats:
            await self.orch.user_text(b)
        self._all = self.drain()


@pytest.fixture
def h() -> VoiceHarness:
    return VoiceHarness()


async def test_full_script_reaches_all_golden_outcomes(h):
    await h.run_to_completion()
    case = h.repo.get()

    # Identity + CRM
    assert case.identity_status is IdentityStatus.identified
    # Credit check ran (consent granted) with the canonical score.
    assert case.credit_result is not None and case.credit_result.score == 781
    # Capacity golden number.
    assert case.capacity_result is not None
    assert case.capacity_result.metrics["kalp_surplus_monthly"] == 5138
    # Advisor summary present and never "approved".
    assert case.advisor_summary is not None
    assert "approv" not in case.advisor_summary.status_text.lower()
    # Meeting booked for the canonical rescheduled slot.
    assert case.booked_meeting is not None
    assert case.booked_meeting.slot.slot_id == "slot-2026-09-21-1500"
    # Card blocked + replacement ordered.
    assert case.cards[0].status is CardStatus.blocked
    assert case.replacement_order is not None

    # The agent surfaced a spoken transcript throughout.
    agent_msgs = [m for m in h._all if m.get("type") == "agent_transcript"]
    assert len(agent_msgs) >= 7
    transcript = " ".join(m["text"] for m in agent_msgs).lower()
    assert "emma" in transcript
    assert "goodbye" in transcript
    stress = transcript.index("7 percent stress rate")
    dti = transcript.index("debt-to-income ratio")
    advisor = transcript.index("human advisor makes the final decision")
    assert stress < dti < advisor
    assert "approved" not in transcript
    assert "denied" not in transcript


async def test_credit_gate_blocks_without_clear_consent():
    h = VoiceHarness()
    from app.domain.fixtures import apply_accepted_income_emma

    case = h.repo.get()
    apply_accepted_income_emma(case)
    h.repo.set(case)
    h._all = []
    await h.orch.start()
    await h.orch.user_text("I'd like a mortgage for a house in Täby.")
    # Ambiguous answer must NOT grant credit-check consent.
    await h.orch.user_text("Hmm, maybe, I'm not sure.")
    assert h.repo.get().credit_result is None  # gate held


async def test_card_block_request_needs_no_second_confirmation():
    h = VoiceHarness()
    from app.domain.fixtures import apply_accepted_income_emma

    case = h.repo.get()
    apply_accepted_income_emma(case)
    h.repo.set(case)
    h._all = []
    await h.orch.start()
    # Drive to the card topic.
    for b in [
        "Mortgage for Täby please.",
        "Yes, run the credit check.",
        "1,750,000 kronor.",
        "Anything after three weeks away?",
        "The 21st of September at 15:00.",
        "My card was stolen; please block it.",
    ]:
        await h.orch.user_text(b)
    assert h.repo.get().cards[0].status is CardStatus.blocked
    assert h.repo.get().replacement_order is not None


async def test_advisor_summary_contract_for_screen3(h):
    """Screen 3 reads advisor_summary.sections — lock its shape + never 'approved'."""
    await h.run_to_completion()
    s = h.repo.get().advisor_summary
    assert s is not None
    assert s.final_decision_required is True
    assert "approv" not in s.status_text.lower()
    assert "approv" not in s.decision_text.lower()
    assert s.status_text == "Preliminary assessment: affordable with advisor note"
    assert s.flags == ["dti_above_guideline"]
    assert s.recommended_action == "advisor_review"
    for key in (
        "identity",
        "income_provenance",
        "requested_loan",
        "credit_result",
        "capacity_metrics",
        "risks_caveats",
        "meeting",
    ):
        assert key in s.sections, key
    assert s.sections["capacity_metrics"]["kalp_surplus_monthly"] == 5138
    assert s.sections["income_provenance"]["net_monthly"] == 62400


async def test_call_starts_with_known_customer_profile():
    h = VoiceHarness()
    h._all = []
    await h.orch.start()
    assert h.repo.get().identity_status is IdentityStatus.identified
    transcript = " ".join(
        message["text"] for message in h.drain() if message.get("type") == "agent_transcript"
    )
    assert "Emma" in transcript


async def test_voice_explains_unreadable_payslip_and_reupload():
    h = VoiceHarness()
    await h.orch.start()
    await h.orch.user_text("Why was my payslip not approved?")
    transcript = " ".join(
        message["text"] for message in h.drain() if message.get("type") == "agent_transcript"
    ).lower()
    assert "too blurry" in transcript
    assert "upload a clearer copy" in transcript


async def test_simulated_call_updates_phone_after_readback_confirmation():
    h = VoiceHarness()
    await h.orch.start()
    await h.orch.user_text("I want to change my phone number.")
    await h.orch.user_text("My new number is 070 555 12 34.")
    assert h.repo.get().customer_profile.phone_number == "+46 70 123 45 67"

    await h.orch.user_text("Yes, that's correct.")
    assert h.repo.get().customer_profile.phone_number == "+46 70 555 12 34"
    transcript = " ".join(
        message["text"] for message in h.drain() if message.get("type") == "agent_transcript"
    )
    assert "Personal information" in transcript
