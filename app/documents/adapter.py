from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Protocol

from azure.ai.contentunderstanding.aio import ContentUnderstandingClient
from azure.identity.aio import DefaultAzureCredential

from app.domain.models import ExtractedField, ExtractedIncome


class PayslipAnalyzer(Protocol):
    async def analyze(self, filename: str, content: bytes, content_type: str) -> ExtractedIncome: ...


class AzureContentUnderstandingPayslipAnalyzer:
    async def analyze(self, filename: str, content: bytes, content_type: str) -> ExtractedIncome:
        del filename
        endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT", "").rstrip("/")
        analyzer_id = os.getenv("CONTENTUNDERSTANDING_ANALYZER_ID", "")
        if not endpoint or not analyzer_id:
            raise RuntimeError("Content Understanding endpoint and analyzer ID must be configured")

        credential = DefaultAzureCredential()
        try:
            async with ContentUnderstandingClient(endpoint=endpoint, credential=credential) as client:
                poller = await client.begin_analyze_binary(
                    analyzer_id=analyzer_id,
                    binary_input=content,
                    content_type=content_type,
                )
                result = await poller.result()
        finally:
            await credential.close()

        if not result.contents or not result.contents[0].fields:
            raise RuntimeError("Content Understanding returned no payslip fields")
        return map_payslip_fields(result.contents[0].fields)


def map_payslip_fields(fields: dict[str, Any]) -> ExtractedIncome:
    def extracted(name: str, converter: Any = None) -> ExtractedField:
        field = fields.get(name)
        value = getattr(field, "value", None) if field is not None else None
        if value is not None and converter is not None:
            value = converter(value)
        source = getattr(field, "source", None) if field is not None else None
        grounding = json.dumps(source.as_dict(), default=str) if hasattr(source, "as_dict") else str(source or "")
        return ExtractedField(
            value=value,
            confidence=getattr(field, "confidence", None) if field is not None else None,
            grounding=grounding or None,
            method="azure-content-understanding",
            provenance="azure-ai-extracted",
            original_value=value,
        )

    def integer(value: Any) -> int:
        return int(round(float(str(value).replace("SEK", "").replace(" ", "").replace(",", ""))))

    def iso_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    return ExtractedIncome(
        employer_name=extracted("employer_name", str),
        gross_salary_monthly=extracted("gross_salary_monthly", integer),
        net_salary_monthly=extracted("net_salary_monthly", integer),
        employment_type=extracted("employment_type", str),
        pay_date=extracted("pay_date", iso_date),
    )


analyzer: PayslipAnalyzer = AzureContentUnderstandingPayslipAnalyzer()
