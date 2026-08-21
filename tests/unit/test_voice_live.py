import json

import pytest

from app.domain.repository import repository
from app.voice.adapter import AzureVoiceLiveSession


class FakeWebSocket:
    pass


@pytest.mark.asyncio
async def test_voice_session_uses_pcm_and_controlled_tool(monkeypatch):
    monkeypatch.setenv("AZURE_VOICELIVE_ENDPOINT", "https://example.services.ai.azure.com")
    session = AzureVoiceLiveSession(FakeWebSocket())
    try:
        config = session.request_session().as_dict()
        assert config["input_audio_sampling_rate"] == 24000
        assert config["input_audio_format"] == "pcm16"
        assert config["output_audio_format"] == "pcm16"
        assert config["turn_detection"]["interrupt_response"] is True
        assert [tool["name"] for tool in config["tools"]] == ["process_customer_request"]
    finally:
        await session.credential.close()


@pytest.mark.asyncio
async def test_voice_tool_preserves_mortgage_policy(monkeypatch, ready_case):
    monkeypatch.setenv("AZURE_VOICELIVE_ENDPOINT", "https://example.services.ai.azure.com")
    repository.save(ready_case)
    session = AzureVoiceLiveSession(FakeWebSocket())
    try:
        result = json.loads(
            await session._process_customer_request(
                {
                    "text": "I want a mortgage",
                    "intent": "start_mortgage",
                    "granted": None,
                    "deposit_sek": None,
                    "after_three_weeks": False,
                    "slot_id": None,
                }
            )
        )
        case = repository.get()
        assert result["reply"] == "May I run an illustrative credit check for this mortgage assessment? Please answer yes or no."
        assert case.consents[-1].action == "credit_check"
        assert case.consents[-1].status == "requested"
        assert case.transcript[-1] == {"speaker": "customer", "text": "I want a mortgage"}
    finally:
        await session.credential.close()