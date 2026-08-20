"""Deterministic Bank Alfa lending policy constants (illustrative demo values).

Every value here is a simplified demo assumption, surfaced to the UI as such.
These are the ONLY knobs the calculator uses; the language model never computes
capacity itself. See docs/functional-specification.md `calculate_borrowing_capacity`.
"""
from __future__ import annotations

from typing import Final

# LTV / amortization thresholds (Swedish amorteringskrav, simplified)
LTV_HIGH_THRESHOLD: Final = 0.70          # > 70 % LTV -> 2 % base amortization
BASE_AMORT_RATE_HIGH_LTV: Final = 0.02    # 2 % of mortgage / year
DEBT_RATIO_THRESHOLD: Final = 4.5         # > 4.5x annual gross -> +1 % amortization
ADDITIONAL_AMORT_RATE: Final = 0.01       # 1 % of mortgage / year

# Stress test + tax
STRESSED_INTEREST_RATE: Final = 0.07      # 7 % stressed annual interest
INTEREST_TAX_ADJUSTMENT: Final = 0.30     # 30 % illustrative interest tax relief

# Household demo costs (SEK / month)
LIVING_COST_MONTHLY: Final = 12_500
PROPERTY_RUNNING_COST_MONTHLY: Final = 6_000

MONTHS_PER_YEAR: Final = 12

# Human-readable assumptions shown alongside the result.
ASSUMPTIONS: Final = [
    "Amortization: 2% of the mortgage per year while LTV is above 70%.",
    "Additional amortization: +1% per year when total debt exceeds 4.5x annual gross income.",
    "Stress test applies a 7% illustrative interest rate.",
    "Interest cost is reduced by a simplified 30% tax adjustment.",
    "Living cost SEK 12,500/month and property running cost SEK 6,000/month are fixed demo figures.",
]

CAVEATS: Final = [
    "All policy figures are simplified demo assumptions, not Bank Alfa's real lending rules.",
    "This is a preliminary, illustrative assessment — never a final lending decision.",
]
