"""Generate the bundled high-confidence Swedish payslip PDF (Lönespecifikation).

Reproducible, deterministic output committed to the repo so the demo is repeatable
without a headless browser or Azure access. All data is fictional — no real personal
data. The five required extraction fields are printed with the canonical values the
simulated Content Understanding analyzer expects, so the deterministic demo keeps
matching:

    employer            = Northstar AB
    Bruttolön           = 96 000 kr
    Nettolön (utbetalas)= 62 400 kr
    Anställningsform     = Tillsvidareanställning
    Utbetalningsdatum   = 2026-08-25

Run:  python scripts/generate_payslip_pdf.py
Output: app/documents/assets/lonespec-northstar-hifi.pdf
"""
from __future__ import annotations

from pathlib import Path

import reportlab.rl_config
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parents[1] / "app" / "documents" / "assets" / "lonespec-northstar-hifi.pdf"

INK = HexColor("#172126")
MUTED = HexColor("#5b6b6a")
LINE = HexColor("#D5DCDA")
RED = HexColor("#C9343A")

PAGE_W, PAGE_H = A4
LEFT = 22 * mm
RIGHT = PAGE_W - 22 * mm
WIDTH = RIGHT - LEFT


def _money(v: int) -> str:
    """Swedish thousands grouping: '96 000 kr'."""
    return f"{v:,}".replace(",", " ") + " kr"


class Sheet:
    def __init__(self, c: canvas.Canvas) -> None:
        self.c = c
        self.y = PAGE_H - 24 * mm

    def _text(self, x, y, s, *, font="Helvetica", size=10, color=INK):
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawString(x, y, s)

    def _right(self, x, y, s, *, font="Helvetica", size=10, color=INK):
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawRightString(x, y, s)

    def hline(self, y, *, color=LINE, width=0.6):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(width)
        self.c.line(LEFT, y, RIGHT, y)

    def section(self, title: str):
        self.y -= 9 * mm
        self._text(LEFT, self.y, title.upper(), font="Helvetica-Bold", size=9, color=MUTED)
        self.y -= 2 * mm
        self.hline(self.y)
        self.y -= 6 * mm

    def kv_two(self, left_k, left_v, right_k, right_v):
        """Two key/value pairs on one row (left column + right column)."""
        mid = LEFT + WIDTH / 2
        self._text(LEFT, self.y, left_k, color=MUTED, size=9)
        self._right(mid - 6 * mm, self.y, left_v, font="Helvetica-Bold")
        if right_k is not None:
            self._text(mid + 6 * mm, self.y, right_k, color=MUTED, size=9)
            self._right(RIGHT, self.y, right_v, font="Helvetica-Bold")
        self.y -= 6.6 * mm

    def amount_row(self, k, v, *, bold=False, color=INK, size=10, muted_key=True):
        self._text(LEFT, self.y, k, color=(MUTED if muted_key else INK), size=9 if muted_key else size)
        self._right(RIGHT, self.y, v, font=("Helvetica-Bold" if bold else "Helvetica"), size=size, color=color)
        self.y -= 6.6 * mm


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Invariant output: fixed creation date + no random doc IDs so regenerating
    # the PDF produces byte-stable output (clean diffs, reproducible builds).
    reportlab.rl_config.invariant = 1
    c = canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("Lönespecifikation — Northstar AB")
    c.setAuthor("Northstar AB lönesystem")
    c.setSubject("Lönespecifikation Augusti 2026")
    s = Sheet(c)

    # ---- Header ------------------------------------------------------- #
    s._text(LEFT, s.y, "Northstar AB", font="Helvetica-Bold", size=18)
    s._right(RIGHT, s.y, "Lönespecifikation", font="Helvetica-Bold", size=15, color=INK)
    s.y -= 6 * mm
    s._text(LEFT, s.y, "ARBETSGIVARE", font="Helvetica-Bold", size=8, color=MUTED)
    s._right(RIGHT, s.y, "Löneperiod: Augusti 2026", size=9, color=MUTED)
    s.y -= 5 * mm
    s._text(LEFT, s.y, "Org.nr 556677-8899", size=9, color=MUTED)
    s._right(RIGHT, s.y, "Utbetalningsdatum: 2026-08-25", font="Helvetica-Bold", size=9, color=INK)
    s.y -= 5 * mm
    s._text(LEFT, s.y, "Kista Science Tower, 164 51 Kista", size=9, color=MUTED)
    s._right(RIGHT, s.y, "Specifikationsnr: 2026-08-4471", size=9, color=MUTED)
    s.y -= 3 * mm
    s.hline(s.y, color=INK, width=1.4)

    # ---- Employee ----------------------------------------------------- #
    s.section("Anställd")
    s.kv_two("Namn", "Emma Lindberg", "Personnummer", "900312-4455")
    s.kv_two("Anställningsnr", "4471", "Befattning", "Systemutvecklare")
    s.kv_two("Adress", "Katrinedalsvägen 12", "Anställningsform", "Tillsvidareanställning")
    s.kv_two("Postort", "183 30 Täby", "Anställd sedan", "2021-04-01")
    s.kv_two("Skattetabell", "31, kolumn 1", "Arbetad tid", "168 tim")

    # ---- Utbetalning -------------------------------------------------- #
    s.section("Utbetalning")
    s.kv_two("Utbetalande bank", "Handelsbanken", "Clearingnr", "6789")
    s.kv_two("Kontonummer", "123 456 789", "Betalsätt", "Insättning (lön)")

    # ---- Lön och tillägg ---------------------------------------------- #
    s.section("Lön och tillägg")
    s.amount_row("Grundlön (månadslön)", _money(88_000))
    s.amount_row("OB-ersättning (kväll/helg)", _money(3_500))
    s.amount_row("Övertidsersättning (12 tim)", _money(4_500))
    s.y -= 1 * mm
    s.hline(s.y)
    s.y -= 5 * mm
    s.amount_row("Bruttolön", _money(96_000), bold=True, size=11, muted_key=False)

    # ---- Avdrag ------------------------------------------------------- #
    s.section("Avdrag")
    s.amount_row("Preliminär skatt (tabell 31)", "-" + _money(33_600))
    s.amount_row("Nettolöneavdrag förmånsbil", _money(0))

    # ---- Nettolön ----------------------------------------------------- #
    s.y -= 1 * mm
    s.hline(s.y, color=INK, width=1.4)
    s.y -= 7 * mm
    s._text(LEFT, s.y, "Nettolön (utbetalas)", font="Helvetica-Bold", size=12, color=INK)
    s._right(RIGHT, s.y, _money(62_400), font="Helvetica-Bold", size=13, color=RED)
    s.y -= 3 * mm

    # ---- Ackumulerat (YTD) + info ------------------------------------- #
    s.section("Ackumulerat i år (jan-aug 2026)")
    s.kv_two("Bruttolön (ack.)", _money(768_000), "Semesterdagar kvar", "18 dagar")
    s.kv_two("Preliminär skatt (ack.)", _money(268_800), "Semesterlön (sparad)", _money(23_100))
    s.kv_two("Nettolön (ack.)", _money(499_200), "Arbetsgivaravgift (31,42 %)", _money(30_163))

    # ---- Footer ------------------------------------------------------- #
    s.y -= 10 * mm
    s.hline(s.y)
    s.y -= 6 * mm
    s.c.setFont("Helvetica", 8)
    s.c.setFillColor(MUTED)
    for i, line in enumerate(
        [
            "Digital lönespecifikation genererad av Northstar AB lönesystem. Beloppen är angivna i svenska kronor (SEK).",
            "Detta är ett fiktivt underlag framtaget för en produktdemonstration. Ingen verklig person eller ekonomi avses.",
        ]
    ):
        s.c.drawString(LEFT, s.y - i * 4.6 * mm, line)

    c.showPage()
    c.save()
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
