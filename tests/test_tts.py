"""TTS endpoint contract: disabled -> 503; enabled -> audio/mpeg bytes; locale mapping."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.speech.tts import _lang_of
from app.state import app_state


class FakeTTS:
    provider = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, bool]] = []

    async def synthesize(self, text: str, voice: str | None = None, lead: bool = False) -> bytes:
        self.calls.append((text, voice, lead))
        return b"ID3-fake-mp3-bytes"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_tts_disabled_returns_503(client, monkeypatch):
    monkeypatch.setattr(app_state, "tts", None)
    resp = client.post("/api/tts", json={"text": "hello"})
    assert resp.status_code == 503


def test_tts_synthesizes_audio(client, monkeypatch):
    fake = FakeTTS()
    monkeypatch.setattr(app_state, "tts", fake)
    resp = client.post("/api/tts", json={"text": "Thank you, Emma."})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"ID3-fake-mp3-bytes"
    assert fake.calls == [("Thank you, Emma.", None, False)]


def test_tts_rejects_empty_text(client, monkeypatch):
    monkeypatch.setattr(app_state, "tts", FakeTTS())
    resp = client.post("/api/tts", json={"text": ""})
    assert resp.status_code == 422


@pytest.mark.parametrize(
    ("voice", "lang"),
    [
        ("en-US-EmmaMultilingualNeural", "en-US"),
        ("sv-SE-SofieNeural", "sv-SE"),
        ("Aria", "en-US"),
    ],
)
def test_lang_derivation(voice, lang):
    assert _lang_of(voice) == lang
