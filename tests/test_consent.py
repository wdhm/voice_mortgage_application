"""Consent classifier + engine: deterministic, fails closed, spends once."""
from __future__ import annotations

import pytest

from app.domain.consent import (
    ConsentDecision,
    ConsentEngine,
    ConsentRequired,
    classify_consent,
)
from app.domain.fixtures import build_canonical_case
from app.domain.models import ConsentAction, ConsentStatus


@pytest.mark.parametrize("text", ["Yes", "yes please", "go ahead", "Sure, do it", "okay", "I consent", "please proceed", "block it"])
def test_classifier_grants(text):
    assert classify_consent(text) is ConsentDecision.grant


@pytest.mark.parametrize("text", ["No", "no thanks", "don't", "stop", "not now", "cancel that"])
def test_classifier_denies(text):
    assert classify_consent(text) is ConsentDecision.deny


@pytest.mark.parametrize("text", ["", "   ", "maybe", "I'm not sure", "what do you mean", "let me think", "not yet", None])
def test_classifier_ambiguous(text):
    assert classify_consent(text) is ConsentDecision.ambiguous


def test_contradiction_fails_closed():
    # "no ... go ahead" must NOT grant (denial precedence).
    assert classify_consent("no, don't go ahead") is ConsentDecision.deny


def test_grant_then_consume_once():
    case = build_canonical_case("s", 0)
    case.identity_status = case.identity_status  # no-op for clarity
    eng = ConsentEngine()
    rec = eng.request(case, ConsentAction.credit_check)
    eng.resolve(case, rec.consent_id, "yes, go ahead")
    assert rec.status is ConsentStatus.granted

    consumed = eng.consume(case, ConsentAction.credit_check)
    assert consumed.status is ConsentStatus.consumed
    # Second consume must fail — a granted consent is spent exactly once.
    with pytest.raises(ConsentRequired):
        eng.consume(case, ConsentAction.credit_check)


def test_ambiguous_leaves_requested():
    case = build_canonical_case("s", 0)
    eng = ConsentEngine()
    rec = eng.request(case, ConsentAction.credit_check)
    eng.resolve(case, rec.consent_id, "maybe later")
    assert rec.status is ConsentStatus.requested
    with pytest.raises(ConsentRequired):
        eng.consume(case, ConsentAction.credit_check)


def test_denied_cannot_be_consumed():
    case = build_canonical_case("s", 0)
    eng = ConsentEngine()
    rec = eng.request(case, ConsentAction.credit_check)
    eng.resolve(case, rec.consent_id, "no")
    assert rec.status is ConsentStatus.denied
    with pytest.raises(ConsentRequired):
        eng.consume(case, ConsentAction.credit_check)


def test_card_scope_must_match():
    case = build_canonical_case("s", 0)
    eng = ConsentEngine()
    rec = eng.request(case, ConsentAction.block_card, resource_scope="card-mc-4471")
    eng.resolve(case, rec.consent_id, "yes")
    # Wrong scope -> not consumable.
    with pytest.raises(ConsentRequired):
        eng.consume(case, ConsentAction.block_card, resource_scope="card-OTHER")
    # Correct scope -> consumable.
    assert eng.consume(case, ConsentAction.block_card, resource_scope="card-mc-4471")


def test_request_supersedes_prior_outstanding():
    case = build_canonical_case("s", 0)
    eng = ConsentEngine()
    first = eng.request(case, ConsentAction.credit_check)
    second = eng.request(case, ConsentAction.credit_check)
    assert first.status is ConsentStatus.expired
    assert second.status is ConsentStatus.requested
