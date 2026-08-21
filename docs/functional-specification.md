# Functional Specification

## Actors

- **Emma Lindberg**: fictional customer and single mortgage applicant.
- **Voice agent**: one Voice Live agent that converses and selects tools.
- **Bank employee**: uses the service side, reviews uncertain document extraction, and monitors the customer case.
- **Mortgage advisor**: receives the summary and owns the final decision.
- **Presenter**: controls samples, DigitalD approval, text fallback, and reset.

## Experience boundaries

### Customer side

The customer route can upload or replace a payslip, view customer-safe document status, complete the simulated DigitalD step, start and control the voice call, provide consent, use text fallback, and see appointment/card confirmations. It must not receive internal confidence diagnostics, credit score, calculation workings, employee notes, tool activity, or review commands.

### Service side

The employee route can see Emma's mock CRM profile, existing products, extraction fields and confidence, document preview and grounding, review tasks, consent state, calculation details, advisor summary, meeting, card outcome, and AI activity. Document approval/rejection and demo reset are service-side actions.

Both sides subscribe to the same case using different API response models and event projections. Hiding fields in React is insufficient; FastAPI must filter them at the endpoint and WebSocket boundaries.

## Core state model

The canonical in-memory case contains:

```text
DemoCase
  case_id
  session_id
  customer_profile
  identity_status
  uploaded_document
  extracted_income
  accepted_income
  review_record
  property_request
  credit_result
  consent_records
  capacity_result
  advisor_summary
  offered_meeting_slots
  booked_meeting
  cards
  replacement_order
  ordered_events
```

Each mutable operation records a timestamp and correlation ID. Reset replaces the entire object with canonical data.

## Part 1 requirements

### Upload

- Accept an image or PDF supported by the configured Content Understanding analyzer.
- Reject unsupported type, empty file, and oversized file before analysis.
- Include one bundled high-confidence and one bundled low-confidence fake Swedish payslip.
- Arbitrary presenter uploads are supported but are not guaranteed to match the schema.

### Extraction schema

| Field | Type | Required | Normalization |
|---|---|---|---|
| `employer_name` | string | yes | trimmed display name |
| `gross_salary_monthly` | currency amount | yes | SEK numeric amount |
| `net_salary_monthly` | currency amount | yes | SEK numeric amount |
| `employment_type` | enum/string | yes | canonical `permanent_full_time` for happy path |
| `pay_date` | date | yes | ISO date plus localized display |

For every field retain value, confidence, source grounding where available, extraction method, and provenance.

### Confidence policy

- Straight-through acceptance requires every required field to be present with confidence greater than or equal to `0.85`.
- A missing confidence on a required field is treated as low confidence.
- Any failed required field routes the whole extraction to `review_required`.
- No extracted income reaches `accepted_income` before automatic acceptance or explicit reviewer approval.
- Bank-employee edits replace the field value and set provenance to `human-approved`; retain the original extraction for comparison.

### Part 1 terminal states

- `accepted_automatically`
- `accepted_after_review`
- `rejected_by_reviewer`
- `analysis_failed`

Only the first two make income available to Part 2.

## Part 2 conversation policy

- Speak English in short, natural turns suitable for voice.
- Identify the customer before exposing CRM details or calling protected tools.
- Reuse accepted income and do not ask Emma to repeat it.
- Ask only for missing mortgage inputs.
- Explain that calculations are preliminary and illustrative.
- Keep the mortgage and stolen-card intents in the same session.
- Never reveal full card numbers or unnecessary personal data.
- Do not execute credit or card-block tools before valid consent.
- Do not state or imply that the mortgage is finally approved.

## Tool contracts

All tools return structured JSON-compatible results internally, even if a concise natural-language summary is returned to Voice Live. Inputs are validated server-side. The model cannot bypass guard conditions.

### `identify_customer_with_digitald`

Purpose: complete the fictional DigitalD handoff after the presenter approves the modal.

Input:

- `case_id`
- `approval_token`: short-lived server-generated demo token, not a real identity credential

Output:

- `customer_id`
- `display_name`
- `identified_at`
- `assurance`: `demo_simulated`

Guard: modal approval must exist for the current session.

### `get_crm_profile`

Purpose: retrieve Emma's mock profile and known products.

Input: `customer_id`

Output includes customer name, contact-safe summary, existing car loan balance/payment, and relationship summary.

Guard: customer identified.

### `run_credit_check`

Purpose: return the deterministic mock credit result.

Input: `customer_id`, `consent_id`

Canonical output:

- internal score `781/999`
- risk band `low`
- existing car-loan balance `SEK 180,000`
- monthly payment `SEK 4,200`
- defaults `none`
- result source `mock_credit_bureau`

Guard: unconsumed, granted credit-check consent for the current customer and session. Mark consent consumed after execution.

### `calculate_borrowing_capacity`

Purpose: apply deterministic illustrative Bank Alfa rules.

Inputs:

- property price
- deposit
- accepted gross and net monthly income
- existing debt balance and monthly payment
- stressed interest rate
- household living cost
- property running cost

Canonical calculation:

| Metric | Formula | Happy-path result |
|---|---|---:|
| Requested mortgage | property price - deposit | SEK 5,250,000 |
| LTV | mortgage / property price | 75.0% |
| Total debt | mortgage + existing debt | SEK 5,430,000 |
| Annual gross income | gross monthly income × 12 | SEK 1,152,000 |
| Debt ratio | total debt / annual gross income | 4.71× |
| Base amortization | 2% of mortgage because LTV > 70% | SEK 8,750/month |
| Additional amortization | 1% because debt ratio > 4.5× | SEK 4,375/month |
| Total amortization | 3% of mortgage | SEK 13,125/month |
| Stressed gross interest | mortgage × 7% / 12 | SEK 30,625/month |
| Illustrative interest tax adjustment | stressed interest × 30% | SEK 9,188/month |
| Stressed net interest | gross interest - adjustment | SEK 21,437/month |
| Living cost | configured demo amount | SEK 12,500/month |
| Property running cost | configured demo amount | SEK 6,000/month |
| Existing debt payment | mock credit result | SEK 4,200/month |
| KALP surplus | net income - all above monthly costs | SEK 5,138/month |

Rounding may differ by one krona. The happy path is `preliminary_positive` because the surplus is positive but narrow. The UI must label the 30% adjustment and all policy values as simplified demo assumptions.

Output includes all inputs, formulas, metrics, outcome, assumptions, and caveats. Do not allow the model to calculate these values itself.

### `write_advisor_summary`

Purpose: create a structured handoff from verified case data.

Input: `case_id`

Output sections: identity, income provenance, requested loan, credit result, capacity metrics, customer preferences, risks/caveats, meeting, and `final_decision_required=true`.

Guard: identified customer, accepted income, credit result, and capacity result exist.

### `get_available_meeting_times`

Purpose: return deterministic mock advisor availability.

Inputs: earliest date, optional preferred time of day, timezone `Europe/Stockholm`.

Behavior:

- First call returns slots within the next week.
- After Emma says she is away for three weeks, a later call with the updated earliest date includes Monday, 21 September 2026 at 15:00.
- Tool never claims access to a real calendar.

### `book_meeting`

Purpose: book the selected mock advisor meeting.

Inputs: customer ID, exact slot ID, purpose.

Canonical output: Monday, 21 September 2026, 15:00-15:45 Europe/Stockholm, mortgage advisor, mock booking reference.

Guard: slot was offered in the current session. Repeated booking of the same slot is idempotent.

### `get_customer_cards`

Purpose: list safe card descriptors.

Input: customer ID

Output includes card type, last four digits, and status. Canonical match is an active Bank Alfa Mastercard ending 4471.

Guard: customer identified.

### `block_card_and_order_replacement`

Purpose: atomically block Mastercard 4471 and create a mock replacement order.

Inputs: customer ID, card ID, reason `stolen`, consent ID.

Output includes blocked status, block timestamp, replacement order reference, and safe delivery estimate.

Guard: unconsumed explicit consent for the exact selected card, action, customer, and current session. Mark consent consumed after execution. Repeated execution returns the existing block and replacement order.

## Consent model

A consent record contains:

- consent ID
- session and customer IDs
- action: `credit_check` or `block_card_and_order_replacement`
- resource scope, including card ID when applicable
- status: requested, granted, denied, expired, consumed
- exact final user transcript
- requested and resolved timestamps

The agent requests consent conversationally. A final affirmative user turn grants it only when the active consent request is unambiguous. Silence, topic changes, “maybe,” or general statements do not grant consent. Denial cancels the action without ending the broader conversation.

## Advisor handoff

The case can be `preliminary_positive`, `preliminary_negative`, or `insufficient_information`. None is a final lending decision. The final state always includes `advisor_decision_required=true` and a visible handoff event.

## Live event contract

Minimum event envelope:

```json
{
  "event_id": "evt-000123",
  "event_type": "tool.completed",
  "session_id": "session-demo",
  "case_id": "case-emma",
  "correlation_id": "corr-...",
  "sequence": 123,
  "timestamp": "2026-09-01T10:15:30Z",
  "display": {
    "label": "Calculate borrowing capacity",
    "status": "completed",
    "service": "Mock mortgage engine"
  }
}
```

The browser contract omits raw document content, model prompts, chain-of-thought, credentials, and unsanitized tool payloads.

## Error behavior

| Failure | Required behavior |
|---|---|
| Unsupported document | Explain accepted formats; do not call Content Understanding. |
| Document analysis timeout | Mark failed, allow retry, keep previous accepted income unchanged. |
| Missing/low confidence | Route to human review. |
| DigitalD declined | Do not reveal CRM data; allow retry or end. |
| Credit consent denied | Do not run credit tool; continue with non-protected help. |
| Protected tool called without consent | Dispatcher rejects it and emits `tool.blocked_by_policy`. |
| Voice disconnect | Stop speaking, show reconnect state, preserve case state. |
| Tool timeout | Never narrate success; offer retry. |
| Meeting slot stale | Fetch availability again. |
| Card already blocked | Return existing safe state and avoid duplicate replacement orders. |
| Reset during call | Confirm, close session, reset all case and event state. |

## Reset contract

Reset must:

1. stop any active Voice Live session
2. clear browser audio buffers and transcript
3. replace all mutable case data with canonical values
4. restore Mastercard 4471 to active with no replacement order
5. remove accepted income and review actions
6. clear consents, credit result, capacity result, meeting, and summary
7. restart event sequence from a documented initial state
