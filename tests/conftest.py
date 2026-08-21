"""Shared test harness: a fresh, isolated tool stack per test (no global singleton)."""
from __future__ import annotations

import pytest

from app.domain.consent import ConsentEngine
from app.domain.fixtures import CASE_ID
from app.domain.repository import InMemoryCaseRepository
from app.events.bus import EventBus
from app.tools.dispatcher import ToolDispatcher


class Stack:
    def __init__(self) -> None:
        self.repo = InMemoryCaseRepository(session_id="session-test")
        self.bus = EventBus(session_id="session-test", case_id=CASE_ID)
        self.bus.set_epoch(self.repo.epoch)
        self.engine = ConsentEngine()
        self.tools = ToolDispatcher(self.repo, self.bus, self.engine)
        self._q = self.bus.subscribe()

    def event_types(self) -> list[str]:
        out = []
        while not self._q.empty():
            out.append(self._q.get_nowait().event_type)
        return out

    async def reset(self) -> None:
        case = self.repo.reset()
        self.bus.reset_history()
        self.bus.set_epoch(case.epoch)


@pytest.fixture
def stack() -> Stack:
    return Stack()
