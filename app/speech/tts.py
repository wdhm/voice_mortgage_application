"""Azure neural text-to-speech behind a tiny port (keyless, same Foundry endpoint).

The assistant's transcript lines are synthesised to MP3 so the browser can play
the reply aloud. Auth is keyless: an AAD token for the Cognitive Services data
plane against the resource's custom domain — the plain-Bearer form the Foundry
`.cognitiveservices.azure.com` endpoint accepts (confirmed against foundry-mortgage).

Any failure raises TTSError; the /api/tts route turns that into a 5xx and the
browser falls back to Web Speech, so the demo never goes silent.
"""
from __future__ import annotations

import asyncio
import html
from typing import Protocol

import httpx

from ..config import settings

_SCOPE = "https://cognitiveservices.azure.com/.default"
_TIMEOUT_S = 30.0


class TTSError(RuntimeError):
    """Synthesis failed (network, auth, or a non-200 from the service)."""


class TextToSpeech(Protocol):
    provider: str

    async def synthesize(self, text: str, voice: str | None = None, lead: bool = False) -> bytes:
        """Return audio bytes (MP3) for the given text.

        ``lead`` prepends a short exact silence so the audio device's warm-up
        (which clips the first ~200ms when playback starts from idle) lands on
        silence instead of the first word.
        """


class FoundryTextToSpeech:
    """Neural TTS via POST {endpoint}/tts/cognitiveservices/v1 (SSML in, MP3 out)."""

    provider = "foundry"

    def __init__(self) -> None:
        self._url = settings.foundry_endpoint.rstrip("/") + "/tts/cognitiveservices/v1"
        self._voice = settings.tts_voice
        self._format = settings.tts_format
        self._credential = None  # lazily created; avoids az login at import time

    async def _token(self) -> str:
        if self._credential is None:
            # Sync credential + thread hop: the async credential needs aiohttp,
            # while the sync one rides azure-core's requests transport (already present).
            from azure.identity import DefaultAzureCredential

            self._credential = DefaultAzureCredential()
        token = await asyncio.to_thread(self._credential.get_token, _SCOPE)
        return token.token

    async def synthesize(self, text: str, voice: str | None = None, lead: bool = False) -> bytes:
        name = voice or self._voice
        lang = _lang_of(name)
        silence = "<mstts:silence type='Leading-exact' value='300ms'/>" if lead else ""
        ssml = (
            "<speak version='1.0' xmlns:mstts='https://www.w3.org/2001/mstts' "
            f"xml:lang='{lang}'>"
            f"<voice xml:lang='{lang}' name='{name}'>{silence}{html.escape(text)}</voice>"
            "</speak>"
        )
        headers = {
            "Authorization": f"Bearer {await self._token()}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": self._format,
            "User-Agent": "bankalfa-mortgage-demo",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.post(self._url, headers=headers, content=ssml.encode("utf-8"))
        except httpx.HTTPError as exc:  # network / timeout
            raise TTSError(str(exc)) from exc
        if resp.status_code != 200 or not resp.content:
            raise TTSError(f"tts failed: {resp.status_code} {resp.text[:200]}")
        return resp.content


def _lang_of(voice: str) -> str:
    """Derive the BCP-47 locale from a neural voice name (e.g. sv-SE-SofieNeural)."""
    parts = voice.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return "en-US"


def make_tts() -> TextToSpeech | None:
    """Construct the configured TTS provider, or None when disabled."""
    if settings.tts_provider == "foundry":
        return FoundryTextToSpeech()
    return None
