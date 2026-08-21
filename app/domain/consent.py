"""Server-owned consent state machine + deterministic transcript classifier.

Consent is NEVER inferred from model output or tool arguments. The dispatcher
calls `consume` immediately before a protected tool runs; consume atomically
verifies a granted, unconsumed consent that matches the exact action, resource
scope, customer and session, then marks it consumed. Classification of the final
user turn is deterministic so a recorded demo is perfectly repeatable.

See docs/functional-specification.md "Consent model".
"""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from enum import Enum

from .models import ConsentAction, ConsentRecord, ConsentStatus, DemoCase


class ConsentDecision(str, Enum):
    grant = "grant"
    deny = "deny"
    ambiguous = "ambiguous"


# Word-boundary phrase sets. Ambiguity and denial fail closed (never grant).
_AMBIGUOUS = [
    r"maybe", r"not sure", r"i'?m not sure", r"don'?t know", r"perhaps",
    r"let me think", r"hold on", r"i guess", r"what do you mean", r"can you explain",
    r"not yet", r"in a (?:moment|minute|bit)", r"later",
]
_DENY = [
    r"\bno\b", r"\bnope\b", r"\bdon'?t\b", r"do not", r"stop", r"cancel",
    r"\bnot now\b", r"i'?d rather not", r"no thanks", r"never", r"skip",
]
_GRANT = [
    r"\byes\b", r"\byeah\b", r"\byep\b", r"\byup\b", r"\bsure\b", r"go ahead",
    r"please do", r"\bdo it\b", r"\bokay\b", r"\bok\b", r"that'?s fine",
    r"i consent", r"i agree", r"absolutely", r"go for it", r"please proceed",
    r"proceed", r"run it", r"block it", r"go right ahead", r"of course",
]


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify_consent(transcript: str | None) -> ConsentDecision:
    """Map a final user turn to grant / deny / ambiguous. Fails closed."""
    if not transcript or not transcript.strip():
        return ConsentDecision.ambiguous
    text = transcript.strip().lower()
    # Precedence: ambiguity first, then denial, then explicit grant.
    if _matches(_AMBIGUOUS, text):
        return ConsentDecision.ambiguous
    if _matches(_DENY, text):
        return ConsentDecision.deny
    if _matches(_GRANT, text):
        return ConsentDecision.grant
    return ConsentDecision.ambiguous


class ConsentRequired(Exception):
    """Raised by consume() when no valid, unconsumed granted consent exists."""

    def __init__(self, action: ConsentAction, resource_scope: str | None) -> None:
        self.action = action
        self.resource_scope = resource_scope
        super().__init__(f"consent required for {action.value} (scope={resource_scope})")


def _now() -> datetime:
    return datetime.now(UTC)


class ConsentEngine:
    """Operates on the consent records held by the DemoCase aggregate.

    Stateless across calls (all state lives on the case), so a reset — which
    rebuilds the case — automatically discards every prior consent.
    """

    def request(
        self,
        case: DemoCase,
        action: ConsentAction,
        *,
        resource_scope: str | None = None,
        customer_id: str | None = None,
    ) -> ConsentRecord:
        # Expire any still-outstanding request for the same action + scope.
        for rec in case.consent_records:
            if (
                rec.action == action
                and rec.resource_scope == resource_scope
                and rec.status == ConsentStatus.requested
            ):
                rec.status = ConsentStatus.expired
                rec.resolved_at = _now()

        record = ConsentRecord(
            consent_id=f"consent-{uuid.uuid4().hex[:10]}",
            session_id=case.session_id,
            customer_id=customer_id or case.customer_profile.customer_id,
            action=action,
            resource_scope=resource_scope,
            status=ConsentStatus.requested,
            requested_at=_now(),
        )
        case.consent_records.append(record)
        return record

    def resolve(
        self, case: DemoCase, consent_id: str, final_transcript: str | None
    ) -> ConsentRecord:
        """Apply the deterministic classifier to a specific requested consent.

        Ambiguous input leaves the consent `requested` (the agent re-prompts);
        only an unambiguous affirmative grants it. Denial cancels it.
        """
        record = self._find(case, consent_id)
        if record is None:
            raise KeyError(f"unknown consent {consent_id}")
        if record.status != ConsentStatus.requested:
            return record

        record.final_user_transcript = final_transcript
        decision = classify_consent(final_transcript)
        if decision is ConsentDecision.grant:
            record.status = ConsentStatus.granted
            record.resolved_at = _now()
        elif decision is ConsentDecision.deny:
            record.status = ConsentStatus.denied
            record.resolved_at = _now()
        # ambiguous -> unchanged (still requested)
        return record

    def consume(
        self,
        case: DemoCase,
        action: ConsentAction,
        *,
        resource_scope: str | None = None,
        customer_id: str | None = None,
        consent_id: str | None = None,
    ) -> ConsentRecord:
        """Atomically verify + consume a granted consent, or raise ConsentRequired.

        Synchronous and allocation-free between check and mutate, so it cannot
        interleave under asyncio — a granted consent is spent exactly once.
        """
        want_customer = customer_id or case.customer_profile.customer_id
        for rec in case.consent_records:
            if rec.status != ConsentStatus.granted:
                continue
            if rec.action != action:
                continue
            if rec.resource_scope != resource_scope:
                continue
            if rec.session_id != case.session_id:
                continue
            if rec.customer_id != want_customer:
                continue
            if consent_id is not None and rec.consent_id != consent_id:
                continue
            rec.status = ConsentStatus.consumed
            rec.resolved_at = _now()
            return rec
        raise ConsentRequired(action, resource_scope)

    @staticmethod
    def _find(case: DemoCase, consent_id: str) -> ConsentRecord | None:
        for rec in case.consent_records:
            if rec.consent_id == consent_id:
                return rec
        return None
