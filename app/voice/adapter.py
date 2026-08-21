from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from contextlib import suppress
from typing import Any

from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioInputTranscriptionOptions,
    AudioNoiseReduction,
    AzureSemanticVadMultilingual,
    AzureStandardVoice,
    FunctionCallOutputItem,
    FunctionTool,
    InputAudioFormat,
    InputTextContentPart,
    MessageItem,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
)
from azure.identity.aio import DefaultAzureCredential
from fastapi import WebSocket, WebSocketDisconnect

from app.conversation.router import CustomerIntent, dispatch_intent
from app.domain.repository import repository
from app.realtime.events import add_event, broker

logger = logging.getLogger(__name__)

VOICE_INSTRUCTIONS = """
You are the voice channel for Bank Alfa's mortgage application demo. Be concise,
calm, and transparent that all decisions are preliminary and illustrative.

For every substantive customer utterance, call process_customer_request with the
customer's complete utterance. Do not answer it yourself. After the tool returns,
speak the reply field exactly, without adding, removing, or paraphrasing words.
Never claim an action happened unless the tool response says it happened. Never
request or reveal passwords, PINs, security codes, or full card numbers.
""".strip()


class VoiceConfigurationError(RuntimeError):
    pass


class AzureVoiceLiveSession:
    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.endpoint = os.getenv("AZURE_VOICELIVE_ENDPOINT", "").rstrip("/")
        self.model = os.getenv("AZURE_VOICELIVE_MODEL", "gpt-realtime-1.5")
        self.api_version = os.getenv("AZURE_VOICELIVE_API_VERSION", "2026-04-10")
        self.voice = os.getenv("AZURE_VOICELIVE_VOICE", "en-US-Ava:DragonHDLatestNeural")
        self.credential = DefaultAzureCredential()
        self.connection: Any = None
        self._response_active = False
        self._pending_calls: dict[str, dict[str, str]] = {}

    def request_session(self) -> RequestSession:
        return RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=VOICE_INSTRUCTIONS,
            voice=AzureStandardVoice(name=self.voice, prefer_locales=["en-US"]),
            input_audio_sampling_rate=24000,
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            input_audio_transcription=AudioInputTranscriptionOptions(
                model="azure-speech",
                language="en-US",
                phrase_list=["Bank Alfa", "Emma Lindberg", "Täby", "DigitalD"],
            ),
            turn_detection=AzureSemanticVadMultilingual(
                threshold=0.65,
                prefix_padding_ms=300,
                silence_duration_ms=600,
                remove_filler_words=True,
                languages=["en-US"],
                auto_truncate=True,
                create_response=True,
                interrupt_response=True,
            ),
            input_audio_echo_cancellation=AudioEchoCancellation(),
            input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),
            tools=[
                FunctionTool(
                    name="process_customer_request",
                    description=(
                        "Classify and process the customer's complete utterance through Bank Alfa's "
                        "controlled mortgage, appointment, consent, and card workflow."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The customer's complete utterance verbatim.",
                            },
                            "intent": {
                                "type": "string",
                                "enum": [
                                    "start_mortgage", "resolve_consent", "provide_deposit",
                                    "request_meeting", "book_meeting", "report_stolen_card", "other"
                                ],
                            },
                            "granted": {"type": ["boolean", "null"]},
                            "deposit_sek": {"type": ["integer", "null"], "minimum": 0},
                            "after_three_weeks": {"type": "boolean"},
                            "slot_id": {"type": ["string", "null"]},
                        },
                        "required": ["text", "intent", "granted", "deposit_sek", "after_three_weeks", "slot_id"],
                        "additionalProperties": False,
                    },
                )
            ],
            tool_choice="auto",
            parallel_tool_calls=False,
            metadata={"application": "voice-mortgage", "channel": "customer-web"},
        )

    async def run(self) -> None:
        if not self.endpoint:
            raise VoiceConfigurationError("AZURE_VOICELIVE_ENDPOINT is not configured")

        try:
            async with connect(
                endpoint=self.endpoint,
                credential=self.credential,
                model=self.model,
                api_version=self.api_version,
                connection_options={"handshake_timeout": 20.0, "heartbeat": 15.0},
            ) as connection:
                self.connection = connection
                await connection.session.update(session=self.request_session())
                await self.websocket.send_json({"type": "voice.status", "status": "connecting"})
                await self._run_connected()
        finally:
            self.connection = None
            await self.credential.close()

    async def _run_connected(self) -> None:
        browser_task = asyncio.create_task(self._receive_browser_audio())
        azure_task = asyncio.create_task(self._receive_azure_events())
        done, pending = await asyncio.wait(
            {browser_task, azure_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in pending:
            with suppress(asyncio.CancelledError):
                await task
        for task in done:
            task.result()

    async def _receive_browser_audio(self) -> None:
        while True:
            message = await self.websocket.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))
            if audio := message.get("bytes"):
                await self.connection.input_audio_buffer.append(
                    audio=base64.b64encode(audio).decode("ascii")
                )
                continue
            if text := message.get("text"):
                payload = json.loads(text)
                if payload.get("type") == "input.text" and str(payload.get("text", "")).strip():
                    await self.connection.conversation.item.create(
                        item=MessageItem(
                            role="user",
                            content=[InputTextContentPart(text=str(payload["text"]).strip())],
                        )
                    )
                    await self.connection.response.create()

    async def _receive_azure_events(self) -> None:
        async for event in self.connection:
            await self._handle_event(event)

    async def _handle_event(self, event: Any) -> None:
        if event.type == ServerEventType.SESSION_UPDATED:
            await self.websocket.send_json({"type": "voice.status", "status": "listening"})
            await self._send_greeting()
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            await self.websocket.send_json({"type": "voice.interrupted"})
            if self._response_active:
                with suppress(Exception):
                    await self.connection.response.cancel()
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            await self.websocket.send_json({"type": "voice.status", "status": "thinking"})
        elif event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
            transcript = str(getattr(event, "transcript", "")).strip()
            if transcript:
                await self.websocket.send_json(
                    {"type": "voice.transcript", "speaker": "customer", "text": transcript, "final": True}
                )
        elif event.type == ServerEventType.RESPONSE_CREATED:
            self._response_active = True
            await self.websocket.send_json({"type": "voice.status", "status": "speaking"})
        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            await self.websocket.send_bytes(event.delta)
        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            await self.websocket.send_json(
                {
                    "type": "voice.transcript",
                    "speaker": "assistant",
                    "text": event.delta,
                    "final": False,
                }
            )
        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
            transcript = str(getattr(event, "transcript", "")).strip()
            if transcript:
                await self._record_assistant_transcript(transcript)
                await self.websocket.send_json(
                    {"type": "voice.transcript", "speaker": "assistant", "text": transcript, "final": True}
                )
        elif event.type == ServerEventType.RESPONSE_DONE:
            self._response_active = False
            await self.websocket.send_json({"type": "voice.status", "status": "listening"})
        elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA:
            self._accumulate_function_call(event)
        elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
            await self._complete_function_call(event)
        elif event.type == ServerEventType.ERROR:
            message = getattr(getattr(event, "error", None), "message", str(event))
            if "no active response" not in message.lower():
                logger.error("Voice Live error: %s", message)
                await self.websocket.send_json({"type": "voice.error", "message": message})

    def _accumulate_function_call(self, event: Any) -> None:
        call_id = str(getattr(event, "call_id", None) or getattr(event, "item_id", "unknown"))
        pending = self._pending_calls.setdefault(call_id, {"name": "", "arguments": ""})
        pending["name"] = str(getattr(event, "name", None) or pending["name"])
        pending["arguments"] += str(getattr(event, "delta", ""))

    async def _complete_function_call(self, event: Any) -> None:
        call_id = str(getattr(event, "call_id", None) or getattr(event, "item_id", "unknown"))
        pending = self._pending_calls.pop(call_id, {"name": "", "arguments": ""})
        name = str(getattr(event, "name", None) or pending["name"])
        raw_arguments = str(getattr(event, "arguments", None) or pending["arguments"] or "{}")
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {}

        if name == "process_customer_request":
            output = await self._process_customer_request(arguments)
        else:
            output = json.dumps({"error": f"Unknown tool: {name}"})

        await self.connection.conversation.item.create(
            item=FunctionCallOutputItem(call_id=call_id, output=output)
        )
        await self.connection.response.create(
            additional_instructions="Speak the tool's reply field exactly and do not add commentary."
        )

    async def _process_customer_request(self, arguments: dict[str, Any]) -> str:
        text = str(arguments.get("text", "")).strip()
        if not text:
            return json.dumps({"reply": "I did not catch that. Please try again."})

        case = repository.get()
        event_count = len(case.events)
        if not case.transcript or case.transcript[-1] != {"speaker": "customer", "text": text}:
            case.transcript.append({"speaker": "customer", "text": text})
        try:
            intent = CustomerIntent.model_validate(arguments)
            reply = dispatch_intent(case, intent, text)
        except Exception as error:
            logger.exception("Mortgage voice tool failed")
            reply = f"I cannot complete that request right now: {error}"
        event = add_event(case, "transcript.completed", "Voice conversation turn", "completed", "Voice Live")
        repository.save(case)
        for new_event in case.events[event_count:]:
            await broker.publish(case, new_event)
        return json.dumps({"reply": reply}, ensure_ascii=False)

    async def _record_assistant_transcript(self, transcript: str) -> None:
        case = repository.get()
        if case.transcript and case.transcript[-1] == {"speaker": "assistant", "text": transcript}:
            return
        case.transcript.append({"speaker": "assistant", "text": transcript})
        repository.save(case)

    async def _send_greeting(self) -> None:
        await self.connection.conversation.item.create(
            item=MessageItem(
                role="system",
                content=[
                    InputTextContentPart(
                        text="Briefly say: Welcome back, Emma. How can I help with your application?"
                    )
                ],
            )
        )
        await self.connection.response.create()
