"""Shared application state: the single repository + event bus for the demo session.

Kept in one place so REST routes, the WebSocket, and (later) the Voice Live and
document flows all operate on the same case and timeline.
"""
from __future__ import annotations

from .domain.fixtures import CASE_ID
from .domain.repository import InMemoryCaseRepository
from .events.bus import EventBus
from .events.models import EventStatus

SESSION_ID = "session-demo"


class AppState:
    def __init__(self) -> None:
        self.repo = InMemoryCaseRepository(session_id=SESSION_ID)
        self.bus = EventBus(session_id=SESSION_ID, case_id=CASE_ID)
        self.bus.set_epoch(self.repo.epoch)

    async def reset(self) -> None:
        """Reset the case (new epoch) and clear the timeline, then emit a reset event."""
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
