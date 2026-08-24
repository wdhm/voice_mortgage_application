"""Azure Voice Live speech-to-speech provider."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from contextlib import AbstractAsyncContextManager
from typing import Any

from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioInputTranscriptionOptions,
    AzureStandardVoice,
    FunctionCallOutputItem,
    FunctionTool,
    InputAudioFormat,
    InputTextContentPart,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
    ServerVad,
    ToolChoiceLiteral,
    UserMessageItem,
)
from azure.core.credentials_async import AsyncTokenCredential

from ..azure_auth import build_async_credential
from ..config import settings
from .agent_spec import SYSTEM_PROMPT, TOOL_SCHEMAS
from .port import ConversationHost

logger = logging.getLogger(__name__)


class FoundryVoiceSession:
    provider = "foundry"

    def __init__(self, host: ConversationHost) -> None:
        self._host = host
        self._credential: AsyncTokenCredential | None = None
        self._connection_context: AbstractAsyncContextManager | None = None
        self._connection: Any = None
        self._receive_task: asyncio.Task | None = None
        self._ready = asyncio.Event()
        self._startup_error: str | None = None
        self._user_transcript_ready = asyncio.Event()
        self._pending_calls: list[tuple[str, str, str, str]] = []

    async def start(self) -> None:
        self._credential = build_async_credential()
        self._connection_context = connect(
            endpoint=settings.foundry_endpoint,
            credential=self._credential,
            model=settings.voicelive_model,
            api_version=settings.voicelive_api_version,
            credential_scopes="https://cognitiveservices.azure.com/.default",
        )
        self._connection = await self._connection_context.__aenter__()
        self._receive_task = asyncio.create_task(self._receive_events())

        tools = [FunctionTool(**schema) for schema in TOOL_SCHEMAS]
        session = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=SYSTEM_PROMPT,
            voice=AzureStandardVoice(name=settings.voicelive_voice),
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            input_audio_echo_cancellation=AudioEchoCancellation(),
            input_audio_transcription=AudioInputTranscriptionOptions(
                model="gpt-4o-mini-transcribe",
                language="en",
            ),
            turn_detection=ServerVad(
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=650,
                auto_truncate=True,
                create_response=True,
                interrupt_response=True,
            ),
            tools=tools,
            tool_choice=ToolChoiceLiteral.AUTO,
        )
        await self._connection.session.update(session=session)
        await asyncio.wait_for(self._ready.wait(), timeout=15)
        if self._startup_error:
            raise RuntimeError(self._startup_error)
        profile = await self._host.call_tool("get_crm_profile")
        if not profile.ok:
            raise RuntimeError("Unable to load the known customer's banking profile.")
        await self._connection.response.create(
            additional_instructions=(
                f"Greet Emma briefly. Safe profile summary: {profile.summary} "
                "Then ask how you can help."
            )
        )

    async def on_user_text(self, text: str) -> None:
        if not self._connection or not text.strip():
            return
        await self._host.user_said(text)
        self._user_transcript_ready.set()
        await self._connection.conversation.item.create(
            item=UserMessageItem(content=[InputTextContentPart(text=text)])
        )
        await self._connection.response.create()

    async def on_user_audio(self, pcm_b64: str) -> None:
        if self._connection and pcm_b64:
            await self._connection.input_audio_buffer.append(audio=pcm_b64)

    async def on_user_audio_commit(self) -> None:
        if self._connection:
            await self._connection.input_audio_buffer.commit()

    async def barge_in(self) -> None:
        if not self._connection:
            return
        await self._connection.response.cancel()
        await self._connection.output_audio_buffer.clear()

    async def close(self) -> None:
        task, self._receive_task = self._receive_task, None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        context, self._connection_context = self._connection_context, None
        self._connection = None
        if context:
            await context.__aexit__(None, None, None)

        credential, self._credential = self._credential, None
        if credential:
            await credential.close()

    async def _receive_events(self) -> None:
        try:
            async for event in self._connection:
                await self._handle_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Voice Live receive loop failed")
            await self._host.push({"type": "error", "message": f"Voice Live connection failed: {exc}"})

    async def _handle_event(self, event: Any) -> None:
        logger.debug("Voice Live event: %s", event.type)
        if event.type == ServerEventType.SESSION_UPDATED:
            self._ready.set()
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            self._user_transcript_ready.clear()
            await self._host.push({"type": "barge_in"})
        elif event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
            if event.transcript.strip():
                await self._host.user_said(event.transcript)
            self._user_transcript_ready.set()
        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            pcm = base64.b64encode(event.delta).decode("ascii")
            await self._host.push({"type": "audio", "pcm": pcm})
        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
            if event.transcript.strip():
                await self._host.say(event.transcript)
        elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
            self._pending_calls.append(
                (event.name, event.call_id, event.item_id, event.arguments)
            )
        elif event.type == ServerEventType.RESPONSE_DONE:
            pending, self._pending_calls = self._pending_calls, []
            for name, call_id, item_id, arguments in pending:
                await self._execute_tool(name, call_id, item_id, arguments)
        elif event.type == ServerEventType.ERROR:
            message = event.error.message
            logger.error("Voice Live service error: %s", message)
            if not self._ready.is_set():
                self._startup_error = message
                self._ready.set()
            await self._host.push({"type": "error", "message": message})

    async def _execute_tool(
        self, name: str, call_id: str, item_id: str, arguments: str
    ) -> None:
        try:
            args = json.loads(arguments) if arguments else {}
            if not isinstance(args, dict):
                raise TypeError("Function arguments must be a JSON object.")
        except (json.JSONDecodeError, TypeError) as exc:
            payload = {"ok": False, "error": f"Invalid function arguments: {exc}"}
        else:
            try:
                if name == "request_customer_consent":
                    await self._host.request_consent(
                        args.get("action", ""), card_id=args.get("card_id")
                    )
                    payload = {"ok": True, "summary": "Consent request opened."}
                else:
                    if name == "run_credit_check":
                        await asyncio.wait_for(
                            self._user_transcript_ready.wait(), timeout=8
                        )
                    outcome = await self._host.call_tool(name, args)
                    payload = {
                        "ok": outcome.ok,
                        "result": outcome.result,
                        "summary": outcome.summary,
                    }
            except (TimeoutError, ValueError) as exc:
                payload = {"ok": False, "error": str(exc)}

        await self._connection.conversation.item.create(
            previous_item_id=item_id,
            item=FunctionCallOutputItem(
                call_id=call_id,
                output=json.dumps(payload),
            ),
        )
        await self._connection.response.create()
