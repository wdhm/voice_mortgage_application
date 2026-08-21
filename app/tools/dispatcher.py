"""Tool dispatcher: the single choke point through which every tool runs.

Responsibilities:
  * emit tool.requested / tool.completed / tool.blocked_by_policy / tool.failed
    timeline events (sanitized — never raw args or results);
  * enforce guards and consent (handlers raise; the dispatcher classifies);
  * serialize execution with a lock and drop results from a superseded epoch
    (post-reset) so stale async tool completions can never mutate a fresh case;
  * own consent request/resolution so voice (M4) and tests share one path.

The model can only ask to run a tool by name; it can never bypass these checks.
"""
from __future__ import annotations

import asyncio

from ..domain.consent import ConsentEngine, ConsentRequired
from ..domain.models import ConsentAction, ConsentRecord, ConsentStatus
from ..domain.repository import CaseRepository
from ..events.bus import EventBus
from ..events.models import EventStatus
from .base import GuardError, ToolInputError, ToolOutcome
from .handlers import HANDLERS


class ToolDispatcher:
    def __init__(self, repo: CaseRepository, bus: EventBus, engine: ConsentEngine) -> None:
        self._repo = repo
        self._bus = bus
        self._engine = engine
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Consent (server-owned; scope never comes from model output)
    # ------------------------------------------------------------------ #
    async def request_consent(
        self,
        action: ConsentAction,
        *,
        resource_scope: str | None = None,
        customer_id: str | None = None,
        correlation_id: str | None = None,
    ) -> ConsentRecord:
        async with self._lock:
            case = self._repo.get()
            record = self._engine.request(
                case, action, resource_scope=resource_scope, customer_id=customer_id
            )
            self._repo.set(case)
        await self._bus.emit(
            event_type="consent.requested",
            label=f"Consent requested: {action.value}"
            + (f" ({resource_scope})" if resource_scope else ""),
            status=EventStatus.required,
            service="Consent engine",
            correlation_id=correlation_id,
        )
        return record

    async def resolve_consent(
        self,
        consent_id: str,
        final_transcript: str | None,
        *,
        correlation_id: str | None = None,
    ) -> ConsentRecord:
        async with self._lock:
            case = self._repo.get()
            record = self._engine.resolve(case, consent_id, final_transcript)
            self._repo.set(case)
        if record.status == ConsentStatus.granted:
            status, label = EventStatus.granted, f"Consent granted: {record.action.value}"
        elif record.status == ConsentStatus.denied:
            status, label = EventStatus.denied, f"Consent denied: {record.action.value}"
        else:
            status, label = EventStatus.required, f"Consent still needed: {record.action.value}"
        await self._bus.emit(
            event_type=f"consent.{record.status.value}",
            label=label,
            status=status,
            service="Consent engine",
            correlation_id=correlation_id,
        )
        return record

    # ------------------------------------------------------------------ #
    # Tool dispatch
    # ------------------------------------------------------------------ #
    async def dispatch(
        self, name: str, args: dict | None = None, *, correlation_id: str | None = None
    ) -> ToolOutcome:
        args = args or {}
        handler = HANDLERS.get(name)
        pretty = name.replace("_", " ").capitalize()

        await self._bus.emit(
            event_type="tool.requested",
            label=pretty,
            status=EventStatus.running,
            service="Tool dispatcher",
            correlation_id=correlation_id,
        )

        if handler is None:
            await self._bus.emit(
                event_type="tool.failed",
                label=f"Unknown tool: {name}",
                status=EventStatus.failed,
                service="Tool dispatcher",
                correlation_id=correlation_id,
            )
            return ToolOutcome(
                ok=False, result={"error": "unknown_tool"}, summary="Unknown tool.",
                service="Tool dispatcher", status=EventStatus.failed, label=pretty,
            )

        async with self._lock:
            epoch_before = self._repo.epoch
            case = self._repo.get()
            try:
                outcome = handler(self._engine, case, args)
            except ConsentRequired as exc:
                await self._emit_blocked(
                    f"Blocked: consent required for {exc.action.value}", correlation_id
                )
                return ToolOutcome(
                    ok=False, result={"error": "consent_required", "action": exc.action.value},
                    summary="This action needs the customer's explicit consent first.",
                    service="Consent engine", status=EventStatus.blocked, label=pretty,
                )
            except GuardError as exc:
                await self._emit_blocked(exc.label, correlation_id)
                return ToolOutcome(
                    ok=False, result={"error": "guard_failed", "detail": str(exc)},
                    summary=str(exc), service="Tool dispatcher",
                    status=EventStatus.blocked, label=pretty,
                )
            except ToolInputError as exc:
                await self._bus.emit(
                    event_type="tool.failed", label=f"{pretty}: invalid input",
                    status=EventStatus.failed, service="Tool dispatcher",
                    correlation_id=correlation_id,
                )
                return ToolOutcome(
                    ok=False, result={"error": "invalid_input", "detail": str(exc)},
                    summary=str(exc), service="Tool dispatcher",
                    status=EventStatus.failed, label=pretty,
                )

            # Epoch guard: a reset during the (synchronous) handler would change
            # the epoch; discard rather than committing stale state.
            if self._repo.epoch != epoch_before:
                return ToolOutcome(
                    ok=False, result={"error": "stale_epoch"},
                    summary="Discarded: demo was reset.", service="Tool dispatcher",
                    status=EventStatus.info, label=pretty,
                )
            self._repo.set(case)

        await self._bus.emit(
            event_type="tool.completed",
            label=outcome.label or pretty,
            status=outcome.status,
            service=outcome.service,
            correlation_id=correlation_id,
        )
        return outcome

    async def _emit_blocked(self, label: str, correlation_id: str | None) -> None:
        await self._bus.emit(
            event_type="tool.blocked_by_policy",
            label=label,
            status=EventStatus.blocked,
            service="Policy guard",
            correlation_id=correlation_id,
        )
