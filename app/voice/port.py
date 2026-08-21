"""RealtimeConversationSession port + the ConversationHost contract.

Two providers implement `RealtimeSession`:
  * foundry  — real Voice Live speech-to-speech (azure-ai-voicelive);
  * simulated — a deterministic, text-driven scripted agent for the recorded demo.

Both are governed identically: they never touch the case, tools, or consent
directly. Everything flows through a `ConversationHost`, which is the single
server-owned choke point (tool dispatch, consent, DigitalD token, and the
sanitized outbound channel to the browser). Providers only *decide what to say
and which tool to ask for*; the host decides whether it is allowed.
"""
from __future__ import annotations

from typing import Protocol

from ..tools.base import ToolOutcome

# Voice Live audio contract (P0b spike): PCM16, 24 kHz, mono.
AUDIO_SAMPLE_RATE = 24_000


class ConversationHost(Protocol):
    """Server-owned operations a conversation provider may perform."""

    @property
    def provider(self) -> str: ...

    def approval_token(self) -> str | None:
        """DigitalD approval token for this session, or None until the presenter approves."""

    async def say(self, text: str, *, final: bool = True) -> None:
        """Surface an agent utterance to the browser transcript."""

    async def user_said(self, text: str, *, final: bool = True) -> None:
        """Record a final user turn: push to transcript AND resolve any pending consent."""

    async def push(self, message: dict) -> None:
        """Send a raw sanitized control/audio message on the voice channel."""

    async def call_tool(self, name: str, args: dict | None = None) -> ToolOutcome:
        """Run a tool through the governed dispatcher (guards + consent enforced)."""

    async def request_consent(self, action: str, *, card_id: str | None = None) -> None:
        """Open a consent request; the next final user turn is classified server-side."""


class RealtimeSession(Protocol):
    """A live conversation with one provider, bound to a ConversationHost."""

    @property
    def provider(self) -> str: ...

    async def start(self) -> None:
        """Begin the session (greeting + DigitalD request)."""

    async def on_digitald_approved(self) -> None:
        """Presenter approved the DigitalD modal."""

    async def on_user_text(self, text: str) -> None:
        """A final user turn arrived as text (text fallback, first-class)."""

    async def on_user_audio(self, pcm_b64: str) -> None:
        """A chunk of user microphone audio (base64 PCM16 24 kHz). Foundry only."""

    async def on_user_audio_commit(self) -> None:
        """The user finished speaking; commit the audio buffer. Foundry only."""

    async def barge_in(self) -> None:
        """Interrupt the agent's current response (stop audio + cancel)."""

    async def close(self) -> None:
        """Tear down the provider session."""
