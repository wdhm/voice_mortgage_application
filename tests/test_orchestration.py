"""Tests for the additive multi-agent orchestration surface (app/agents).

These exercise the deterministic orchestration design and stay green offline,
whether or not the optional ``agent-framework`` package is installed.
"""
from __future__ import annotations

from app.agents import (
    AGENT_FRAMEWORK_AVAILABLE,
    CardAgent,
    MortgageAgent,
    VoiceOrchestratorAgent,
    build_orchestration_workflow,
)


def test_module_imports_cleanly() -> None:
    # AGENT_FRAMEWORK_AVAILABLE is a bool regardless of the environment.
    assert isinstance(AGENT_FRAMEWORK_AVAILABLE, bool)


def test_card_agent_exposes_expected_actions() -> None:
    agent = CardAgent()
    assert agent.name == "card_agent"
    assert agent.action_names == ["list_cards", "block_card", "order_replacement"]


def test_mortgage_agent_exposes_expected_actions() -> None:
    agent = MortgageAgent()
    assert agent.name == "mortgage_agent"
    assert agent.action_names == [
        "check_income_status",
        "estimate_borrowing",
        "book_advisor_meeting",
    ]


def test_orchestrator_routes_card_intent_to_card_agent() -> None:
    orchestrator = VoiceOrchestratorAgent()
    specialist = orchestrator.route("Hi, I've lost my card and need it blocked.")
    assert specialist is not None
    assert specialist.name == "card_agent"


def test_orchestrator_routes_mortgage_intent_to_mortgage_agent() -> None:
    orchestrator = VoiceOrchestratorAgent()
    specialist = orchestrator.route("Is my payslip enough for the mortgage advisor meeting?")
    assert specialist is not None
    assert specialist.name == "mortgage_agent"


def test_orchestrator_returns_none_for_unrelated_intent() -> None:
    orchestrator = VoiceOrchestratorAgent()
    assert orchestrator.route("What are your opening hours?") is None


def test_ambiguous_intent_prefers_card_agent() -> None:
    orchestrator = VoiceOrchestratorAgent()
    specialist = orchestrator.route("My card is lost and I also have a mortgage question.")
    assert specialist is not None
    assert specialist.name == "card_agent"


def test_handoff_by_name_returns_specialist() -> None:
    orchestrator = VoiceOrchestratorAgent()
    assert orchestrator.handoff("mortgage_agent").name == "mortgage_agent"


def test_card_agent_block_card_matches_and_orders_replacement() -> None:
    agent = CardAgent()
    blocked = agent.handle("block_card", last_four="4821", reason="lost")
    assert blocked["blocked"] is True
    assert blocked["reason"] == "lost"
    replacement = agent.handle("order_replacement", card_id=blocked["card_id"])
    assert replacement["replacement_order_reference"].startswith("RPL-")


def test_card_agent_block_card_unknown_last_four() -> None:
    agent = CardAgent()
    result = agent.handle("block_card", last_four="0000")
    assert result["blocked"] is False


def test_mortgage_agent_estimate_borrowing_is_illustrative() -> None:
    agent = MortgageAgent()
    result = agent.handle("estimate_borrowing", purchase_price=4_000_000, deposit=800_000)
    assert result["indicative_loan_amount"] == 3_200_000
    assert result["loan_to_value"] == 0.8
    assert "advisor" in result["disclaimer"].lower()


def test_unknown_action_raises() -> None:
    agent = CardAgent()
    try:
        agent.handle("nonexistent_action")
    except KeyError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("expected KeyError for unknown action")


def test_build_workflow_without_framework_raises_cleanly() -> None:
    orchestrator = VoiceOrchestratorAgent()
    if AGENT_FRAMEWORK_AVAILABLE:  # pragma: no cover - depends on optional install.
        return
    try:
        build_orchestration_workflow(orchestrator)
    except RuntimeError as exc:
        assert "agent-framework" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected RuntimeError when framework is absent")
