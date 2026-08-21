from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import uuid4

from app.domain.models import ActivityEvent, DemoCase


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, object]]]] = defaultdict(set)

    def subscribe(self, role: str) -> asyncio.Queue[dict[str, object]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._subscribers[role].add(queue)
        return queue

    def unsubscribe(self, role: str, queue: asyncio.Queue[dict[str, object]]) -> None:
        self._subscribers[role].discard(queue)

    async def publish(self, case: DemoCase, event: ActivityEvent) -> None:
        for role, queues in self._subscribers.items():
            projected = project_event(event, role)
            if projected is not None:
                for queue in queues.copy():
                    await queue.put(projected)


def add_event(
    case: DemoCase,
    event_type: str,
    label: str,
    status: str,
    service: str,
    correlation_id: str | None = None,
) -> ActivityEvent:
    sequence = len(case.events) + 1
    event = ActivityEvent(
        event_id=f"evt-{sequence:06d}",
        event_type=event_type,
        session_id=case.session_id,
        case_id=case.case_id,
        correlation_id=correlation_id or f"corr-{uuid4().hex[:12]}",
        sequence=sequence,
        display={"label": label, "status": status, "service": service},
    )
    case.events.append(event)
    return event


def project_event(event: ActivityEvent, role: str) -> dict[str, object] | None:
    if role == "customer":
        if event.event_type.startswith(("tool.", "consent.", "handoff.")):
            return None
        if event.event_type.startswith("document."):
            return {
                "event_id": event.event_id,
                "event_type": "document.status_changed",
                "sequence": event.sequence,
                "timestamp": event.timestamp.isoformat(),
            }
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "sequence": event.sequence,
            "timestamp": event.timestamp.isoformat(),
        }
    return event.model_dump(mode="json")


broker = EventBroker()
