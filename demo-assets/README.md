# Fictional payslip samples

The customer UI exposes two generated, fictional sample uploads:

- `high-confidence-payslip.pdf` produces the canonical Northstar AB extraction with every required confidence at or above `0.85`.
- `low-confidence-payslip.pdf` produces the same fictional source values with gross salary confidence at `0.72`, requiring employee review.

The starter adapter keys behavior from the explicit sample selector, not document contents. Replace these generated sample payloads with designed PDF or image assets when the real Content Understanding adapter is implemented.