"""Application configuration, loaded from environment / .env (keyless auth)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Microsoft Foundry (Azure AI Services)
    foundry_endpoint: str = "https://foundry-mortgage.cognitiveservices.azure.com/"
    voicelive_model: str = "gpt-realtime-1.5"

    # Content Understanding
    cu_api_version: str = "2025-11-01"
    cu_analyzer_id: str = "bankalfa-payslip"

    # Provider selection: "foundry" (real Azure) or "simulated" (deterministic, offline)
    voice_provider: str = "foundry"
    document_provider: str = "foundry"

    # App
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"


settings = Settings()
