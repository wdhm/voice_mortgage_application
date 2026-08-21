"""Sanitized live-event envelope for the 'under the hood' timeline.

The browser only ever sees this projection — never raw documents, model prompts,
chain-of-thought, credentials, or full card numbers. Every event carries a
monotonic sequence and the case epoch so the UI can order events and discard
anything emitted before the most recent reset.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"
    review = "review"
    granted = "granted"
    denied = "denied"
    required = "required"
    info = "info"


class EventDisplay(BaseModel):
    label: str
    status: EventStatus
    service: str | None = None  # e.g. "Content Understanding", "Voice Live", "Mock CRM"


class Event(BaseModel):
    event_id: str
    event_type: str  # dotted family, e.g. "tool.completed", "consent.granted"
    session_id: str
    case_id: str
    correlation_id: str
    sequence: int
    epoch: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    display: EventDisplay
