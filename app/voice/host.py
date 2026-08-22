"""ConversationHost implementation + the VoiceOrchestrator that owns a live session.

The host is the *only* way a conversation provider can affect the case: it routes
tool calls through the guarded dispatcher, opens/resolves consent through the
server-owned engine (classifying the real final user transcript), injects the
consent scopes server-side, and fans sanitized
transcript/audio/control messages out to the browser voice channel.
"""
from __future__ import annotations

import asyncio
import logging

from ..domain.models import ConsentAction, ConsentStatus
from ..domain.repository import CaseRepository
from ..events.bus import EventBus
from ..tools.base import ToolOutcome
from ..tools.dispatcher import ToolDispatcher
from .port import RealtimeSession

logger = logging.getLogger(__name__)

_ACTION_MAP = {
    "credit_check": ConsentAction.credit_check,
    "block_card": ConsentAction.block_card,
}


class VoiceChannel:
    """Fan-out of sanitized voice messages (transcript, audio, control) to browsers."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def publish(self, message: dict) -> None:
        for q in list(self._subscribers):
            await q.put(message)


class ConversationHost:
    """Governed operations exposed to a conversation provider (see port.ConversationHost)."""

    def __init__(
        self,
        repo: CaseRepository,
        bus: EventBus,
        tools: ToolDispatcher,
        channel: VoiceChannel,
        provider: str,
    ) -> None:
        self._repo = repo
        self._bus = bus
        self._tools = tools
        self._channel = channel
        self._provider = provider

    @property
    def provider(self) -> str:
        return self._provider

    # ---- Outbound to browser -------------------------------------------- #
    async def say(self, text: str, *, final: bool = True) -> None:
        await self._channel.publish({"type": "agent_transcript", "text": text, "final": final})

    async def push(self, message: dict) -> None:
        await self._channel.publish(message)

    async def user_said(self, text: str, *, final: bool = True) -> None:
        await self._channel.publish({"type": "user_transcript", "text": text, "final": final})
        if final:
            await self._resolve_pending_consent(text)

    # ---- Governed tool dispatch ----------------------------------------- #
    async def call_tool(self, name: str, args: dict | None = None) -> ToolOutcome:
        args = dict(args or {})
        if name == "run_credit_check":
            args["customerId"] = self._repo.get().customer_profile.customer_id
        elif name == "write_advisor_summary":
            args["caseId"] = self._repo.get().case_id
        return await self._tools.dispatch(name, args)

    # ---- Consent (server-owned) ----------------------------------------- #
    async def request_consent(self, action: str, *, card_id: str | None = None) -> None:
        mapped = _ACTION_MAP.get(action)
        if mapped is None:
            raise ValueError(f"Unsupported consent action: {action}")
        if mapped is ConsentAction.block_card and not card_id:
            raise ValueError("A card_id is required for card-block consent.")
        scope = card_id if mapped is ConsentAction.block_card else None
        rec = await self._tools.request_consent(mapped, resource_scope=scope)
        await self._channel.publish(
            {"type": "consent", "status": "requested", "action": action, "scope": scope,
             "consent_id": rec.consent_id}
        )

    async def _resolve_pending_consent(self, transcript: str) -> None:
        # Resolve the most recent still-open consent request against the real transcript.
        case = self._repo.get()
        pending = [r for r in case.consent_records if r.status == ConsentStatus.requested]
        if not pending:
            return
        rec = pending[-1]
        resolved = await self._tools.resolve_consent(rec.consent_id, transcript)
        await self._channel.publish(
            {"type": "consent", "status": resolved.status.value, "action": resolved.action.value,
             "scope": resolved.resource_scope, "consent_id": resolved.consent_id}
        )


class VoiceOrchestrator:
    """Owns the single active conversation session and routes browser control messages."""

    def __init__(self, repo: CaseRepository, bus: EventBus, tools: ToolDispatcher, provider: str) -> None:
        self._repo = repo
        self._bus = bus
        self._tools = tools
        self._provider = provider
        self.channel = VoiceChannel()
        self._host: ConversationHost | None = None
        self._session: RealtimeSession | None = None
        self._lock = asyncio.Lock()

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def active(self) -> bool:
        return self._session is not None

    def _build_session(self, host: ConversationHost) -> RealtimeSession:
        if self._provider == "foundry":
            from .foundry import FoundryVoiceSession

            return FoundryVoiceSession(host)
        from .simulated import SimulatedVoiceSession

        return SimulatedVoiceSession(host)

    async def start(self) -> bool:
        async with self._lock:
            await self._close_locked()
            self._host = ConversationHost(
                self._repo, self._bus, self._tools, self.channel, self._provider
            )
            self._session = self._build_session(self._host)
            try:
                await self._session.start()
            except Exception:
                logger.exception("Unable to start %s voice session", self._provider)
                await self._close_locked()
                await self.channel.publish(
                    {
                        "type": "error",
                        "message": f"Unable to start the {self._provider} voice session.",
                    }
                )
                await self.channel.publish(
                    {"type": "session", "state": "idle", "provider": self._provider}
                )
                return False
        await self.channel.publish(
            {"type": "session", "state": "active", "provider": self._provider}
        )
        return True

    async def user_text(self, text: str) -> None:
        if self._session:
            await self._session.on_user_text(text)

    async def user_audio(self, pcm_b64: str) -> None:
        if self._session:
            await self._session.on_user_audio(pcm_b64)

    async def user_audio_commit(self) -> None:
        if self._session:
            await self._session.on_user_audio_commit()

    async def barge_in(self) -> None:
        if self._session:
            await self._session.barge_in()
        await self.channel.publish({"type": "barge_in"})

    async def stop(self) -> None:
        async with self._lock:
            await self._close_locked()
        await self.channel.publish({"type": "session", "state": "idle", "provider": self._provider})

    async def _close_locked(self) -> None:
        if self._session:
            try:
                await self._session.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup on teardown
                pass
        self._session = None
        self._host = None
