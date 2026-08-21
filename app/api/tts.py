"""Text-to-speech endpoint: synthesise an assistant line to MP3 for the browser.

Governance-free by design — this only voices text the server already produced and
surfaced on the transcript. When TTS_PROVIDER is off (or synthesis fails) the route
returns a 5xx and the browser falls back to Web Speech, so playback never blocks.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..speech.tts import TTSError
from ..state import app_state

router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str | None = None


@router.post("/api/tts")
async def synthesize_speech(req: TTSRequest) -> Response:
    tts = app_state.tts
    if tts is None:
        raise HTTPException(status_code=503, detail="tts provider disabled")
    try:
        audio = await tts.synthesize(req.text, req.voice)
    except TTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )
