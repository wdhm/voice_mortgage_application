"""Multi-agent orchestration surface for the Bank Alfa voice demo.

This package layers a Microsoft Agent Framework style *orchestrator + sub-agents*
view on top of the existing governed tool surface. It is additive and illustrative:
it mirrors the real tool names in ``app/tools/handlers.py`` so a presentation can
show how a single VOICE orchestrator hands the conversation off to a ``CardAgent``
or a ``MortgageAgent``. The runtime demo flow (``app/voice``) is untouched.
"""
from __future__ import annotations

from .orchestration import (
    AGENT_FRAMEWORK_AVAILABLE,
    CardAgent,
    MortgageAgent,
    VoiceOrchestratorAgent,
    build_orchestration_workflow,
)

__all__ = [
    "AGENT_FRAMEWORK_AVAILABLE",
    "CardAgent",
    "MortgageAgent",
    "VoiceOrchestratorAgent",
    "build_orchestration_workflow",
]
