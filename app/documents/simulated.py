"""Deterministic simulated Content Understanding analyzer.

Returns canonical, fixed extractions for the two bundled samples so a recorded
demo is perfectly repeatable. The high-confidence sample extracts straight
through; the low-confidence sample has sub-threshold net pay + employment type
(and a just-under pay date) that force the human-review path.

Uploads are routed deterministically by content: uploading the bundled
high-confidence payslip PDF (identified by an exact SHA-256 match of the
committed asset) extracts straight through exactly like the sample, so the
customer can *upload their own payslip* and still hit the marquee path. Any
other upload gets a deterministic low-confidence result so the live upload and
human-review experience can be demonstrated without Azure access. The UI labels
this output as simulated; genuine document extraction uses the Foundry provider.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache

from .port import AnalyzerResult, FieldExtraction
from .samples import sample_pdf_path


@lru_cache(maxsize=1)
def _canonical_high_sha256() -> str | None:
    """SHA-256 of the committed high-confidence payslip PDF (or None if absent)."""
    path = sample_pdf_path("high_confidence")
    if path is None:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_canonical_high(content: bytes) -> bool:
    canonical = _canonical_high_sha256()
    return canonical is not None and hashlib.sha256(content).hexdigest() == canonical


def _high() -> dict[str, FieldExtraction]:
    return {
        "employer_name": FieldExtraction("Northstar AB", "Northstar AB", 0.98, "top: Arbetsgivare"),
        "gross_salary_monthly": FieldExtraction("96 000 kr", 96000, 0.97, "Bruttolön"),
        "net_salary_monthly": FieldExtraction("62 400 kr", 62400, 0.96, "Nettolön (utbetalas)"),
        "employment_type": FieldExtraction(
            "Tillsvidareanställning", "permanent_full_time", 0.94, "Anställningsform"
        ),
        "pay_date": FieldExtraction("2026-08-25", "2026-08-25", 0.95, "Utbetalningsdatum"),
    }


def _low() -> dict[str, FieldExtraction]:
    # Smudged scan: employer + gross still legible; net, employment and date are not.
    return {
        "employer_name": FieldExtraction("Northstar AB", "Northstar AB", 0.91, "top: Arbetsgivare"),
        "gross_salary_monthly": FieldExtraction("96 000 kr", 96000, 0.88, "Bruttolön"),
        "net_salary_monthly": FieldExtraction("6? 400 kr", None, 0.52, "Nettolön (utbetalas)"),
        "employment_type": FieldExtraction("Tillsvidar…", "permanent_full_time", 0.61, "Anställningsform"),
        "pay_date": FieldExtraction("2026-08-25", "2026-08-25", 0.83, "Utbetalningsdatum"),
    }


def _generic() -> dict[str, FieldExtraction]:
    # A customer re-upload represents a new, clearer copy in the recorded demo.
    # The extraction succeeds, but DocumentService still routes direct uploads to
    # a human advisor before the income becomes verified.
    return _high()


class SimulatedDocumentAnalyzer:
    provider = "simulated"

    async def analyze(
        self,
        *,
        content: bytes,
        content_type: str,
        filename: str,
        sample_key: str | None = None,
    ) -> AnalyzerResult:
        if sample_key == "high_confidence":
            fields = _high()
        elif sample_key == "low_confidence":
            fields = _low()
        elif sample_key is None and _is_canonical_high(content):
            # Customer uploaded the genuine bundled payslip PDF.
            fields = _high()
        else:
            fields = _generic()
        return AnalyzerResult(
            provider=self.provider,
            analyzer_id="bankalfa-payslip-sim",
            method="prebuilt-simulated",
            fields=fields,
        )
