"""Case repository — isolates in-memory demo state behind an interface so a
persistent implementation could replace it later without touching tools.

Single active demo session (per architecture.md). Reset replaces the whole
case and bumps the epoch.
"""
from __future__ import annotations

from typing import Protocol

from .fixtures import build_canonical_case
from .models import DemoCase


class CaseRepository(Protocol):
    def get(self) -> DemoCase: ...
    def set(self, case: DemoCase) -> None: ...
    def reset(self) -> DemoCase: ...
    @property
    def epoch(self) -> int: ...


class InMemoryCaseRepository:
    """Process-local single-case repository."""

    def __init__(self, session_id: str = "session-demo") -> None:
        self._session_id = session_id
        self._epoch = 0
        self._case = build_canonical_case(session_id, epoch=self._epoch)

    def get(self) -> DemoCase:
        return self._case

    def set(self, case: DemoCase) -> None:
        self._case = case

    def reset(self) -> DemoCase:
        """Bump the epoch and replace the case with canonical data."""
        self._epoch += 1
        self._case = build_canonical_case(self._session_id, epoch=self._epoch)
        return self._case

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def session_id(self) -> str:
        return self._session_id
