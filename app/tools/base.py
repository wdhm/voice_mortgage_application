"""Shared tool types: guard errors and the structured outcome every tool returns."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..events.models import EventStatus


class GuardError(Exception):
    """A precondition (identity, prior step, offered slot) was not met."""

    def __init__(self, message: str, *, label: str = "Guard failed") -> None:
        self.label = label
        super().__init__(message)


class ToolInputError(Exception):
    """Server-side validation of the tool arguments failed."""


@dataclass
class ToolOutcome:
    ok: bool
    result: dict
    summary: str
    service: str
    status: EventStatus = EventStatus.completed
    label: str = ""
    idempotent_replay: bool = False
    consent_consumed: str | None = None
    meta: dict = field(default_factory=dict)
