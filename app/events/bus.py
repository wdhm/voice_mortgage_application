"""In-memory async event bus.

Assigns monotonic sequence numbers, stamps the current epoch, keeps a bounded
history for late subscribers, and fans out to connected WebSocket clients.
Single-process, single-session (per architecture.md).
"""
from __future__ import annotations

import asyncio
import uuid

from .models import Event, EventDisplay, EventStatus


class EventBus:
    def __init__(self, session_id: str, case_id: str) -> None:
        self.session_id = session_id
        self.case_id = case_id
        self._sequence = 0
        self._epoch = 0
        self._history: list[Event] = []
        self._subscribers: set[asyncio.Queue[Event]] = set()

    # -- lifecycle ------------------------------------------------------- #
    def set_epoch(self, epoch: int) -> None:
        self._epoch = epoch

    def reset_history(self) -> None:
        """Clear timeline history (called on demo reset)."""
        self._history.clear()

    # -- publish --------------------------------------------------------- #
    async def emit(
        self,
        event_type: str,
        label: str,
        status: EventStatus,
        service: str | None = None,
        correlation_id: str | None = None,
    ) -> Event:
        self._sequence += 1
        event = Event(
            event_id=f"evt-{self._sequence:06d}",
            event_type=event_type,
            session_id=self.session_id,
            case_id=self.case_id,
            correlation_id=correlation_id or f"corr-{uuid.uuid4().hex[:12]}",
            sequence=self._sequence,
            epoch=self._epoch,
            display=EventDisplay(label=label, status=status, service=service),
        )
        self._history.append(event)
        for q in list(self._subscribers):
            q.put_nowait(event)
        return event

    # -- subscribe ------------------------------------------------------- #
    def history(self) -> list[Event]:
        return list(self._history)

    def subscribe(self) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(q)
