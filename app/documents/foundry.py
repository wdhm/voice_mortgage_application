"""Real Microsoft Foundry Content Understanding analyzer (keyless).

This is the production target behind the same DocumentAnalyzer port. It is NOT
the recorded-demo path (DOCUMENT_PROVIDER=simulated is), but it lets an operator
run genuine Content Understanding when the `bankalfa-payslip` analyzer exists.
Any failure raises AnalysisError; the service surfaces the active provider so the
demo never silently substitutes one for the other.

API: POST {endpoint}contentunderstanding/analyzers/{id}:analyze?api-version=...
with the document bytes; poll the returned Operation-Location; read fields with
per-field confidence enabled via the estimateFieldSourceAndConfidence feature.
"""
from __future__ import annotations

import asyncio

import httpx

from ..config import settings
from .port import REQUIRED_FIELDS, AnalysisError, AnalyzerResult, FieldExtraction

_SCOPE = "https://cognitiveservices.azure.com/.default"
_POLL_INTERVAL_S = 1.0
_POLL_TIMEOUT_S = 30.0


class FoundryDocumentAnalyzer:
    provider = "foundry"

    def __init__(self) -> None:
        self._endpoint = settings.foundry_endpoint.rstrip("/")
        self._analyzer_id = settings.cu_analyzer_id
        self._api_version = settings.cu_api_version
        self._credential = None  # lazily created; avoids az login at import time

    async def _token(self) -> str:
        if self._credential is None:
            from azure.identity.aio import DefaultAzureCredential

            self._credential = DefaultAzureCredential()
        token = await self._credential.get_token(_SCOPE)
        return token.token

    async def analyze(
        self,
        *,
        content: bytes,
        content_type: str,
        filename: str,
        sample_key: str | None = None,
    ) -> AnalyzerResult:
        url = (
            f"{self._endpoint}/contentunderstanding/analyzers/{self._analyzer_id}:analyze"
            f"?api-version={self._api_version}&features=estimateFieldSourceAndConfidence"
        )
        headers = {
            "Authorization": f"Bearer {await self._token()}",
            "Content-Type": content_type or "application/octet-stream",
        }
        try:
            async with httpx.AsyncClient(timeout=_POLL_TIMEOUT_S) as client:
                resp = await client.post(url, headers=headers, content=content)
                if resp.status_code not in (200, 202):
                    raise AnalysisError(f"analyze failed: {resp.status_code} {resp.text[:200]}")
                result = await self._resolve(client, resp, headers)
        except httpx.HTTPError as exc:  # network/timeout
            raise AnalysisError(str(exc)) from exc

        return AnalyzerResult(
            provider=self.provider,
            analyzer_id=self._analyzer_id,
            method="content-understanding",
            fields=self._map_fields(result),
        )

    async def _resolve(self, client: httpx.AsyncClient, resp: httpx.Response, headers: dict) -> dict:
        if resp.status_code == 200:
            return resp.json()
        op_url = resp.headers.get("Operation-Location")
        if not op_url:
            raise AnalysisError("missing Operation-Location for async analyze")
        deadline = asyncio.get_event_loop().time() + _POLL_TIMEOUT_S
        poll_headers = {"Authorization": headers["Authorization"]}
        while True:
            poll = await client.get(op_url, headers=poll_headers)
            body = poll.json()
            status = (body.get("status") or "").lower()
            if status in ("succeeded", "completed"):
                return body
            if status in ("failed", "canceled"):
                raise AnalysisError(f"analysis {status}")
            if asyncio.get_event_loop().time() > deadline:
                raise AnalysisError("analysis timed out")
            await asyncio.sleep(_POLL_INTERVAL_S)

    def _map_fields(self, body: dict) -> dict[str, FieldExtraction]:
        # Tolerant to minor shape differences across CU result envelopes.
        result = body.get("result") or body
        contents = result.get("contents") or result.get("documents") or []
        raw = contents[0].get("fields", {}) if contents else result.get("fields", {})
        out: dict[str, FieldExtraction] = {}
        for name in REQUIRED_FIELDS:
            f = raw.get(name) or {}
            value = f.get("valueString") or f.get("content") or f.get("value")
            normalized = f.get("valueNumber", f.get("valueDate", value))
            out[name] = FieldExtraction(
                value=str(value) if value is not None else None,
                normalized_value=normalized,
                confidence=f.get("confidence"),
                source_grounding=(f.get("source") or None),
            )
        return out
