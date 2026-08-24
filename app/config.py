"""Application configuration, loaded from environment / .env (keyless auth)."""
from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Microsoft Foundry (Azure AI Services)
    foundry_endpoint: str = "https://foundry-mortgage.cognitiveservices.azure.com/"
    azure_ai_access_token: SecretStr | None = None
    azure_ai_key: SecretStr | None = None
    voicelive_model: str = "gpt-realtime-1.5"
    voicelive_api_version: str = "2026-07-15"
    voicelive_voice: str = "en-US-AvaNeural"

    # Content Understanding
    cu_api_version: str = "2025-11-01"
    cu_analyzer_id: str = "bankalfa_payslip"

    # Provider selection: "foundry" (real Azure) or "simulated" (deterministic, offline)
    voice_provider: str = "foundry"
    document_provider: str = "simulated"

    # Text-to-speech for the assistant's spoken replies: "foundry" (Azure neural
    # via the same keyless Foundry endpoint) or "off" (browser speech handles it).
    tts_provider: str = "off"
    tts_voice: str = "en-US-Ava:DragonHDLatestNeural"
    tts_format: str = "audio-24khz-48kbitrate-mono-mp3"

    # App
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"


settings = Settings()
