"""Voice orchestrator with card and mortgage sub-agents (Microsoft Agent Framework).

This module expresses the demo's conversational design as a *handoff orchestration*:
a single **VoiceOrchestratorAgent** acts as the front-line agent and hands the
conversation off to one of two specialists —

* **CardAgent** — lost/blocked cards and replacements.
* **MortgageAgent** — payslip/income status, borrowing estimate and advisor booking.

It is built against the Microsoft Agent Framework unified Python SDK (pip package
``agent-framework``: ``ChatAgent`` / ``AgentThread`` and the ``HandoffBuilder``
handoff pattern). The framework is an *optional* dependency — see the ``agents``
extra in ``pyproject.toml`` — so the import degrades gracefully and this module,
its tests and ``ruff`` stay green without the package or any network access.

The action bodies are intentionally illustrative: they mirror the governed tools in
``app/tools/handlers.py`` (``get_customer_cards``, ``block_card_and_order_replacement``,
``check_income_status``, ``calculate_borrowing_capacity``, ``get_available_meeting_times``,
``book_meeting``) by name and shape, but do not invoke them or call any LLM. The real
runtime path in ``app/voice`` remains the single source of truth for live behaviour.

Run a scripted handover demo with::

    python -m app.agents.orchestration
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any

# --------------------------------------------------------------------------- #
# Optional Microsoft Agent Framework import.
#
# When ``agent-framework`` is installed (``pip install "bank-alfa-mortgage-demo[agents]"``)
# we bind the real ``ChatAgent`` / ``AgentThread`` / ``HandoffBuilder`` symbols and can
# compose a genuine handoff workflow. Without it, the classes below still describe the
# exact same orchestration so the module remains importable and testable offline.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - exercised only when the optional package is present.
    from agent_framework import AgentThread, ChatAgent, HandoffBuilder

    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:  # pragma: no cover - default offline / CI path.
    AgentThread = ChatAgent = HandoffBuilder = None  # type: ignore[assignment]
    AGENT_FRAMEWORK_AVAILABLE = False


# --------------------------------------------------------------------------- #
# Card specialist tools (mirror ``get_customer_cards`` / ``block_card_and_order_replacement``).
# --------------------------------------------------------------------------- #
_DEMO_CARDS: list[dict[str, str]] = [
    {"card_id": "card-debit-001", "card_type": "Debit", "last_four": "4821", "status": "active"},
    {"card_id": "card-credit-002", "card_type": "Credit", "last_four": "7390", "status": "active"},
]


def list_cards() -> dict[str, Any]:
    """List the customer's cards using safe descriptors only (last four digits)."""
    return {"cards": [dict(card) for card in _DEMO_CARDS]}


def block_card(
    last_four: Annotated[str, "The last four digits the customer stated out loud."],
    reason: Annotated[str, "Why the card is blocked: 'lost', 'stolen' or 'other'."] = "stolen",
) -> dict[str, Any]:
    """Block the exact card matching ``last_four`` and confirm a replacement is on its way."""
    card = next((c for c in _DEMO_CARDS if c["last_four"] == last_four), None)
    if card is None:
        return {"blocked": False, "error": "no_matching_card", "last_four": last_four}
    normalised = reason if reason in {"lost", "stolen", "other"} else "other"
    return {
        "blocked": True,
        "card_id": card["card_id"],
        "last_four": card["last_four"],
        "reason": normalised,
        "status": "blocked",
    }


def order_replacement(
    card_id: Annotated[str, "The card_id returned by block_card / list_cards."],
) -> dict[str, Any]:
    """Order a replacement card and return the reference and delivery estimate."""
    return {
        "card_id": card_id,
        "replacement_order_reference": f"RPL-{uuid.uuid4().hex[:8].upper()}",
        "delivery_estimate": "3-5 business days to your registered address",
    }


# --------------------------------------------------------------------------- #
# Mortgage specialist tools (mirror ``check_income_status`` / ``calculate_borrowing_capacity``
# / ``get_available_meeting_times`` / ``book_meeting``).
# --------------------------------------------------------------------------- #
def check_income_status() -> dict[str, Any]:
    """Report whether the uploaded payslip is accepted and the income is verified."""
    return {
        "document_state": "accepted_automatically",
        "income_verified": True,
        "employer_name": "Nordic Retail AB",
        "gross_salary_monthly": 42000,
        "net_salary_monthly": 31500,
    }


def estimate_borrowing(
    purchase_price: Annotated[int, "Property purchase price in SEK."],
    deposit: Annotated[int, "Customer deposit in SEK."],
) -> dict[str, Any]:
    """Compute a preliminary, illustrative borrowing capacity (an advisor decides)."""
    loan_amount = max(purchase_price - deposit, 0)
    ltv = round(loan_amount / purchase_price, 3) if purchase_price else 0.0
    return {
        "purchase_price": purchase_price,
        "deposit": deposit,
        "indicative_loan_amount": loan_amount,
        "loan_to_value": ltv,
        "affordable_at_stress_rate": ltv <= 0.85,
        "disclaimer": "Preliminary and illustrative — a human advisor makes the final decision.",
    }


def book_advisor_meeting(
    slot_id: Annotated[str, "One of the offered advisor slot ids."],
    purpose: Annotated[str, "Short reason for the meeting."] = "Mortgage application review",
) -> dict[str, Any]:
    """Book one of the offered mortgage advisor slots by its slot_id."""
    return {
        "booked": True,
        "slot_id": slot_id,
        "purpose": purpose,
        "confirmation_reference": f"BK-{uuid.uuid4().hex[:6].upper()}",
    }


# --------------------------------------------------------------------------- #
# Agent definitions.
# --------------------------------------------------------------------------- #
@dataclass
class SubAgent:
    """A specialist agent: a name, instructions and a registry of callable actions."""

    name: str
    description: str
    instructions: str
    actions: dict[str, Callable[..., Any]] = field(default_factory=dict)

    @property
    def action_names(self) -> list[str]:
        """The action names this specialist exposes to the orchestrator."""
        return list(self.actions)

    def handle(self, action: str, /, **kwargs: Any) -> Any:
        """Invoke one of this agent's actions by name."""
        if action not in self.actions:
            raise KeyError(f"{self.name} has no action {action!r}; known: {self.action_names}")
        return self.actions[action](**kwargs)

    def as_chat_agent(self, chat_client: Any = None) -> Any:
        """Materialise a real ``ChatAgent`` when the Agent Framework is installed.

        The tools passed are the very same callables used by :meth:`handle`, so the
        illustrative dispatcher and a live framework agent share one action surface.
        """
        if not AGENT_FRAMEWORK_AVAILABLE:  # pragma: no cover - offline path.
            raise RuntimeError(
                "agent-framework is not installed; install the 'agents' extra to build ChatAgents."
            )
        return ChatAgent(  # pragma: no cover - requires the optional package.
            chat_client=chat_client,
            name=self.name,
            description=self.description,
            instructions=self.instructions,
            tools=list(self.actions.values()),
        )


def CardAgent() -> SubAgent:
    """The card specialist: lost/stolen/blocked cards and replacements."""
    return SubAgent(
        name="card_agent",
        description="Handles lost, stolen or blocked cards and orders replacements.",
        instructions=(
            "You are Bank Alfa's card specialist. Confirm the last four digits, block only "
            "the exact matching card, capture whether it was lost, stolen or blocked for "
            "another reason, then order a replacement. Never reveal full card numbers."
        ),
        actions={
            "list_cards": list_cards,
            "block_card": block_card,
            "order_replacement": order_replacement,
        },
    )


def MortgageAgent() -> SubAgent:
    """The mortgage specialist: income status, borrowing estimate and advisor booking."""
    return SubAgent(
        name="mortgage_agent",
        description="Handles payslip/income status, borrowing estimates and advisor bookings.",
        instructions=(
            "You are Bank Alfa's mortgage specialist. Check the customer's payslip and income "
            "status, give a preliminary and illustrative borrowing estimate, and book a "
            "mortgage advisor appointment. Always state that a human advisor makes the final "
            "lending decision; never say the mortgage is approved."
        ),
        actions={
            "check_income_status": check_income_status,
            "estimate_borrowing": estimate_borrowing,
            "book_advisor_meeting": book_advisor_meeting,
        },
    )


# Keyword intents used by the deterministic router. This is a lightweight illustrative
# stand-in for the model-driven handoff tools the orchestrator emits at runtime.
_CARD_KEYWORDS = ("card", "lost", "stolen", "block", "replacement")
_MORTGAGE_KEYWORDS = (
    "mortgage",
    "loan",
    "borrow",
    "payslip",
    "income",
    "salary",
    "advisor",
    "appointment",
    "meeting",
    "deposit",
)


class VoiceOrchestratorAgent:
    """Front-line VOICE agent that routes to, and hands off to, the specialist agents.

    At runtime this is the Voice Live model; here it is expressed as a deterministic
    orchestrator so the handoff design is importable, testable and demo-able offline.
    """

    name = "voice_orchestrator"
    description = "Front-line Bank Alfa voice agent that hands off to specialist sub-agents."

    def __init__(self) -> None:
        self.card_agent = CardAgent()
        self.mortgage_agent = MortgageAgent()
        self._by_name = {a.name: a for a in (self.card_agent, self.mortgage_agent)}

    @property
    def sub_agents(self) -> list[SubAgent]:
        """The specialists this orchestrator can hand off to."""
        return [self.card_agent, self.mortgage_agent]

    def route(self, utterance: str) -> SubAgent | None:
        """Pick the specialist a customer utterance should be handed off to.

        Returns ``None`` when nothing matches, so the orchestrator can keep the turn
        itself (ask a clarifying question) rather than guess.
        """
        text = utterance.lower()
        card_hit = any(word in text for word in _CARD_KEYWORDS)
        mortgage_hit = any(word in text for word in _MORTGAGE_KEYWORDS)
        if card_hit and not mortgage_hit:
            return self.card_agent
        if mortgage_hit and not card_hit:
            return self.mortgage_agent
        if card_hit and mortgage_hit:
            # Ambiguous: prefer the card path (safety-sensitive) but stay explicit.
            return self.card_agent
        return None

    def handoff(self, target: str | SubAgent) -> SubAgent:
        """Hand the conversation to a named specialist, returning the active sub-agent."""
        if isinstance(target, SubAgent):
            return target
        if target not in self._by_name:
            raise KeyError(f"Unknown sub-agent {target!r}; known: {list(self._by_name)}")
        return self._by_name[target]

    def build_workflow(self, chat_client: Any = None) -> Any:
        """Compose a real Agent Framework handoff workflow when the package is present."""
        return build_orchestration_workflow(self, chat_client=chat_client)


def build_orchestration_workflow(
    orchestrator: VoiceOrchestratorAgent | None = None,
    *,
    chat_client: Any = None,
) -> Any:
    """Build a Microsoft Agent Framework ``HandoffBuilder`` workflow for the orchestration.

    Requires the optional ``agent-framework`` package. The orchestrator is the start
    agent and each specialist is a handoff participant, so the framework generates the
    ``handoff_to_card_agent`` / ``handoff_to_mortgage_agent`` tools automatically.
    """
    if not AGENT_FRAMEWORK_AVAILABLE:  # pragma: no cover - offline path.
        raise RuntimeError(
            "agent-framework is not installed. Install the optional 'agents' extra: "
            'pip install "bank-alfa-mortgage-demo[agents]"'
        )
    orchestrator = orchestrator or VoiceOrchestratorAgent()  # pragma: no cover
    coordinator = ChatAgent(  # pragma: no cover - requires the optional package.
        chat_client=chat_client,
        name=orchestrator.name,
        description=orchestrator.description,
        instructions=(
            "You are Bank Alfa's front-line voice agent for the known customer Emma Lindberg. "
            "Assess each request and hand off to 'card_agent' for card issues or 'mortgage_agent' "
            "for payslip, borrowing or advisor-booking requests, calling the matching handoff tool."
        ),
    )
    specialists = [a.as_chat_agent(chat_client) for a in orchestrator.sub_agents]  # pragma: no cover
    return (  # pragma: no cover - requires the optional package.
        HandoffBuilder()
        .participants([coordinator, *specialists])
        .with_start_agent(coordinator)
        .build()
    )


def _demo() -> None:
    """Print a scripted handover sequence for a live presentation."""
    orchestrator = VoiceOrchestratorAgent()
    framework = "installed" if AGENT_FRAMEWORK_AVAILABLE else "not installed (illustrative mode)"
    print(f"Bank Alfa voice orchestration demo - Microsoft Agent Framework: {framework}\n")

    utterance = "Hi, I think I've lost my card."
    print(f'Customer: "{utterance}"')
    specialist = orchestrator.route(utterance)
    assert specialist is not None
    print(f"  orchestrator -> handoff to {specialist.name} (actions: {specialist.action_names})")
    print(f"  {specialist.name}.list_cards() -> {specialist.handle('list_cards')}")
    blocked = specialist.handle("block_card", last_four="4821", reason="lost")
    print(f"  {specialist.name}.block_card(last_four='4821', reason='lost') -> {blocked}")
    replacement = specialist.handle("order_replacement", card_id=blocked["card_id"])
    print(f"  {specialist.name}.order_replacement(...) -> {replacement}\n")

    utterance = "Also, is my payslip enough for the mortgage? Can I book the advisor?"
    print(f'Customer: "{utterance}"')
    specialist = orchestrator.route(utterance)
    assert specialist is not None
    print(f"  orchestrator -> handoff to {specialist.name} (actions: {specialist.action_names})")
    print(f"  {specialist.name}.check_income_status() -> {specialist.handle('check_income_status')}")
    booked = specialist.handle("book_advisor_meeting", slot_id="slot-2026-09-03-am")
    print(f"  {specialist.name}.book_advisor_meeting(slot_id='slot-2026-09-03-am') -> {booked}")


if __name__ == "__main__":
    _demo()
