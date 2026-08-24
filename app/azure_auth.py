"""Azure credential selection shared by live Foundry providers."""
from __future__ import annotations

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential

from .config import settings


def build_async_credential() -> AsyncTokenCredential:
    if settings.azure_credential_mode == "cli":
        return AzureCliCredential(process_timeout=60)
    return DefaultAzureCredential(process_timeout=60)
