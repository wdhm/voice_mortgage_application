"""DocumentAnalyzer port: the single interface both providers implement.

The real (Foundry Content Understanding) and simulated analyzers return the same
`AnalyzerResult`, so the service layer and UI never branch on provider — only the
explicit `provider` label is surfaced so the demo never silently fakes anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

# The five required payslip fields (docs/functional-specification.md extraction schema).
REQUIRED_FIELDS = (
    "employer_name",
    "gross_salary_monthly",
    "net_salary_monthly",
    "employment_type",
    "pay_date",
)

# Accepted upload types + size ceiling (validated before any analysis).
ACCEPTED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/tiff",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class UploadValidationError(Exception):
    """Raised for unsupported type, empty, or oversized uploads (pre-analysis)."""


class AnalysisError(Exception):
    """Raised when the analyzer fails or times out."""


@dataclass
class FieldExtraction:
    value: str | None
    normalized_value: float | str | None
    confidence: float | None  # None == missing == treated as low confidence
    source_grounding: str | None = None


@dataclass
class AnalyzerResult:
    provider: str          # "simulated" | "foundry"
    analyzer_id: str
    method: str            # e.g. "prebuilt-simulated" | "content-understanding"
    fields: dict[str, FieldExtraction] = field(default_factory=dict)


class DocumentAnalyzer(Protocol):
    @property
    def provider(self) -> str: ...

    async def analyze(
        self,
        *,
        content: bytes,
        content_type: str,
        filename: str,
        sample_key: str | None = None,
    ) -> AnalyzerResult: ...
