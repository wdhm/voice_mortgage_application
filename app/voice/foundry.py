"""Foundry Voice Live provider — real speech-to-speech (filled in M4c).

Placeholder so provider selection never breaks at import time. Selecting the
foundry provider before M4c lands raises a clear, actionable error rather than
an ImportError deep in the orchestrator.
"""
from __future__ import annotations

from .port import ConversationHost


class FoundryVoiceSession:
    provider = "foundry"

    def __init__(self, host: ConversationHost) -> None:  # pragma: no cover - until M4c
        raise NotImplementedError(
            "The foundry Voice Live provider is not wired yet (M4c). "
            "Run with VOICE_PROVIDER=simulated for the scripted demo path."
        )
