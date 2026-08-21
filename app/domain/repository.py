from __future__ import annotations

from copy import deepcopy
from threading import RLock

from app.domain.fixture import canonical_case
from app.domain.models import DemoCase


class InMemoryCaseRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._case = canonical_case()

    def get(self) -> DemoCase:
        with self._lock:
            return deepcopy(self._case)

    def save(self, case: DemoCase) -> DemoCase:
        with self._lock:
            self._case = deepcopy(case)
            return deepcopy(self._case)

    def reset(self) -> DemoCase:
        with self._lock:
            self._case = canonical_case()
            return deepcopy(self._case)


repository = InMemoryCaseRepository()