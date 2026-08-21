"""Deterministic simulated Content Understanding analyzer.

Returns canonical, fixed extractions for the two bundled samples so a recorded
demo is perfectly repeatable. The high-confidence sample extracts straight
through; the low-confidence sample has sub-threshold net pay + employment type
(and a just-under pay date) that force the human-review path. Arbitrary presenter
uploads get a deterministic low-confidence result so the live upload and
human-review experience can be demonstrated without Azure access. The UI labels
this output as simulated; genuine document extraction uses the Foundry provider.
"""
from __future__ import annotations

from .port import AnalyzerResult, FieldExtraction


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
    return _low()


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
        else:
            fields = _generic()
        return AnalyzerResult(
            provider=self.provider,
            analyzer_id="bankalfa-payslip-sim",
            method="prebuilt-simulated",
            fields=fields,
        )
