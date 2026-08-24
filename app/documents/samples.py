"""Two bundled fake Swedish payslips (Lönespecifikation). All data is fictional; no
real personal data.

The high-confidence sample is a real, detailed PDF committed to the repo
(``assets/lonespec-northstar-hifi.pdf``, produced by ``scripts/generate_payslip_pdf.py``)
so the customer uploads/previews an actual ``application/pdf`` document. The
low-confidence sample is likewise a real committed PDF
(``assets/lonespec-northstar-scan.pdf``) — a visibly blurred scan — served as
``application/pdf`` to justify the human-review path. The bundled HTML renderer
below is retained as a defensive fallback (and for the test harness).
"""
from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

SAMPLES = [
    {
        "key": "high_confidence",
        "label": "High-confidence payslip",
        "description": "Crisp digital payslip — extracts straight through.",
        "filename": "lonespec-northstar-hifi.pdf",
        # Real committed PDF asset served as application/pdf for preview + analysis.
        "pdf": "lonespec-northstar-hifi.pdf",
    },
    {
        "key": "low_confidence",
        "label": "Low-confidence payslip",
        "description": "Degraded scan — routes to human review.",
        "filename": "lonespec-northstar-scan.pdf",
        # Real committed blurred PDF asset served as application/pdf for preview + analysis.
        "pdf": "lonespec-northstar-scan.pdf",
    },
]

SAMPLE_KEYS = {s["key"] for s in SAMPLES}


def sample_pdf_path(key: str) -> Path | None:
    """Absolute path to a sample's bundled PDF asset, or None if it has no PDF."""
    meta = next((s for s in SAMPLES if s["key"] == key), None)
    if not meta or "pdf" not in meta:
        return None
    path = ASSETS_DIR / meta["pdf"]
    return path if path.is_file() else None

_BASE_CSS = """
:root{--ink:#172126;--muted:#5b6b6a;--line:#D5DCDA;--red:#C9343A;--paper:#fff;}
*{box-sizing:border-box}
body{margin:0;background:#eceeed;font-family:'Space Grotesk',system-ui,sans-serif;color:var(--ink);}
.sheet{max-width:640px;margin:20px auto;background:var(--paper);padding:34px 40px 40px;
  box-shadow:0 1px 0 var(--line),0 12px 30px rgba(23,33,38,.08);}
.top{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid var(--ink);padding-bottom:14px;}
.brand{font-weight:700;font-size:20px;letter-spacing:.02em}
.brand small{display:block;font-weight:500;color:var(--muted);font-size:12px;letter-spacing:.14em;text-transform:uppercase}
.doc{ text-align:right;font-size:12px;color:var(--muted)}
h1{font-family:'Fraunces',Georgia,serif;font-size:22px;margin:22px 0 4px}
.sub{color:var(--muted);font-size:13px;margin:0 0 20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 28px;font-size:13px}
.row{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:7px 0}
.row .k{color:var(--muted)}
.row .v{font-weight:600;font-variant-numeric:tabular-nums}
.totals{margin-top:22px;border-top:2px solid var(--ink);padding-top:12px}
.totals .row{border:none;padding:5px 0}
.net{font-size:17px}
.net .v{color:var(--red)}
.foot{margin-top:26px;color:var(--muted);font-size:11px;line-height:1.5}
.smudge{filter:blur(1.1px);opacity:.72;letter-spacing:.4px}
.scan{background:linear-gradient(102deg,#fdfdfb,#f3f1ea);}
.scan .sheet{transform:rotate(-.5deg)}
.scan .sheet:after{content:"";position:absolute}
"""


def _payslip(*, net_html: str, emp_html: str, degraded: bool) -> str:
    body_class = "scan" if degraded else ""
    note = (
        "Skannad kopia — vissa fält kan vara svårlästa."
        if degraded
        else "Digital lönespecifikation genererad av Northstar AB lönesystem."
    )
    return f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{_BASE_CSS}</style></head>
<body class="{body_class}"><div class="sheet" style="position:relative">
  <div class="top">
    <div class="brand">Northstar AB<small>Arbetsgivare</small></div>
    <div class="doc">Org.nr 556677-8899<br>Löneperiod: Augusti 2026<br>Utbetalningsdatum: 2026-08-25</div>
  </div>
  <h1>Lönespecifikation</h1>
  <p class="sub">Emma Lindberg · Anställningsnr 4471 · Täby</p>
  <div class="grid">
    <div class="row"><span class="k">Anställningsform</span><span class="v {'smudge' if degraded else ''}">{emp_html}</span></div>
    <div class="row"><span class="k">Befattning</span><span class="v">Systemutvecklare</span></div>
    <div class="row"><span class="k">Skattetabell</span><span class="v">31</span></div>
    <div class="row"><span class="k">Arbetad tid</span><span class="v">168 tim</span></div>
  </div>
  <div class="totals">
    <div class="row"><span class="k">Bruttolön</span><span class="v">96 000 kr</span></div>
    <div class="row"><span class="k">Preliminär skatt</span><span class="v">−33 600 kr</span></div>
    <div class="row net"><span class="k">Nettolön (utbetalas)</span><span class="v {'smudge' if degraded else ''}">{net_html}</span></div>
  </div>
  <p class="foot">{note}</p>
</div></body></html>"""


def render_payslip_html(key: str) -> str:
    if key == "high_confidence":
        return _payslip(net_html="62 400 kr", emp_html="Tillsvidareanställning", degraded=False)
    if key == "low_confidence":
        # Net pay and employment form are smudged/garbled on the scan.
        return _payslip(net_html="6&#8202;2&nbsp;4&#8203;0&#8202;0 k&#8202;r", emp_html="Tillsvidar⋯ställn.", degraded=True)
    raise KeyError(f"unknown sample {key}")
