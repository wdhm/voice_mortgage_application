"""Shared application state: the single repository + event bus for the demo session.

Kept in one place so REST routes, the WebSocket, and (later) the Voice Live and
document flows all operate on the same case and timeline.
"""
from __future__ import annotations

from .config import settings
from .documents.port import DocumentAnalyzer
from .documents.service import DocumentService
from .documents.simulated import SimulatedDocumentAnalyzer
from .domain.consent import ConsentEngine
from .domain.fixtures import CASE_ID
from .domain.repository import InMemoryCaseRepository
from .events.bus import EventBus
from .events.models import EventStatus
from .speech.tts import TextToSpeech, make_tts
from .tools.dispatcher import ToolDispatcher
from .voice.host import VoiceOrchestrator

SESSION_ID = "session-demo"


def _make_analyzer() -> DocumentAnalyzer:
    if settings.document_provider == "foundry":
        from .documents.foundry import FoundryDocumentAnalyzer

        return FoundryDocumentAnalyzer()
    return SimulatedDocumentAnalyzer()


class AppState:
    def __init__(self) -> None:
        self.repo = InMemoryCaseRepository(session_id=SESSION_ID)
        self.bus = EventBus(session_id=SESSION_ID, case_id=CASE_ID)
        self.bus.set_epoch(self.repo.epoch)
        self.consent = ConsentEngine()
        self.tools = ToolDispatcher(self.repo, self.bus, self.consent)
        self.documents = DocumentService(self.repo, self.bus, _make_analyzer())
        self.voice = VoiceOrchestrator(self.repo, self.bus, self.tools, settings.voice_provider)
        self.tts: TextToSpeech | None = make_tts()
        # Bytes of the most recently analyzed document, so the advisor can preview
        # the exact source the customer uploaded. Sanitized: never exposed as an
        # analyzer payload, only streamed back as the original file. Cleared on reset.
        self.last_document_bytes: bytes | None = None
        self.last_document_content_type: str | None = None

    def remember_document(self, content: bytes, content_type: str | None) -> None:
        self.last_document_bytes = content
        self.last_document_content_type = content_type or "application/octet-stream"

    async def reset(self) -> None:
        """Reset the case (new epoch) and clear the timeline, then emit a reset event."""
        await self.voice.stop()
        self.last_document_bytes = None
        self.last_document_content_type = None
        case = self.repo.reset()
        self.bus.reset_history()
        self.bus.set_epoch(case.epoch)
        await self.bus.emit(
            event_type="case.reset",
            label="Demo reset to canonical state",
            status=EventStatus.info,
            service="Demo",
        )


app_state = AppState()
