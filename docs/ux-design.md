# UX and Design Specification

## Design intent

Bank Alfa should feel like a modern Nordic retail bank: clear, calm, trustworthy, and operational rather than promotional. The interface is a live work surface, not a landing page.

The visual direction uses a bright neutral base, dark ink text, restrained red for Bank Alfa identity, teal for verified/completed states, amber for review, and red only for destructive or blocked states. Avoid a monochromatic blue banking template, oversized marketing headings, nested cards, decorative gradients, and excessive rounded pills.

## Desktop layout

The primary presentation viewport is a 16:9 laptop or projected display.

```text
+-----------------------------------------------------------------------+
| Bank Alfa | Mortgage case: Emma Lindberg | Reset demo | Connection    |
+------------------------------------------+----------------------------+
| CUSTOMER JOURNEY                         | UNDER THE HOOD             |
|                                          |                            |
| Step navigation                          | Live timeline              |
| 1 Income document                        | status  operation          |
| 2 Voice application                      |                            |
| 3 Advisor summary                        | Consent and handoff events |
|                                          |                            |
| Active customer task                     | Foundry service labels     |
| Transcript / document review / summary   |                            |
+------------------------------------------+----------------------------+
```

- Customer journey: approximately 62% width.
- Under-the-hood panel: approximately 38% width and always visible.
- Header: compact, fixed height, with brand, case identity, reset, and connection status.
- Do not place the main experience inside a floating page card.
- Repeated timeline events may use compact cards with radius no greater than 8px.

## Mobile and narrow screens

The demo is optimized for desktop, but must remain functional on mobile.

- Customer journey occupies the first view.
- Under-the-hood content becomes a second tab, not a panel below an unbounded transcript.
- Voice controls remain reachable near the bottom safe area.
- Document fields stack without horizontal scrolling.
- No text, status, or button may overlap at 360px width.

## Global controls

- Bank Alfa wordmark: text treatment, not an imitation of a real bank.
- Case indicator: `Emma Lindberg · Mortgage application`.
- Reset icon button with tooltip: requires confirmation if a session is active.
- Connection indicator: disconnected, connecting, ready, reconnecting, failed.
- Presenter mode is implicit; do not add explanatory feature copy to the live screen.

## Navigation and progress

Use a compact three-step control:

1. Income document
2. Voice application
3. Advisor summary

Completed steps show a check icon. A review-required step shows an amber alert icon. The presenter may revisit either independent part without losing accepted income unless reset is used.

## Screen 1: income document

### Empty state

- Large but restrained upload area for PDF, PNG, JPEG, and supported image formats.
- Upload button with file icon.
- Secondary sample selector with `High-confidence payslip` and `Low-confidence payslip`.
- File constraints appear adjacent to the chooser, not as a feature tutorial.

### Analyzing state

- Uploaded document preview remains visible.
- A stable extraction field list shows skeleton values.
- The activity panel adds `Content Understanding · Analyze payslip · Running`.
- Disable duplicate submission while analysis is active.

### Accepted state

- Two-column arrangement: document preview on the left, extracted fields on the right.
- Each field shows label, normalized value, confidence percentage, and verified icon.
- Selecting a field highlights its grounded source region in the preview where available.
- Confirmation strip: `Income details saved to Emma's mortgage case`.
- Primary command: `Continue to voice application`.

### Review-required state

- Amber banner: `Human review required`.
- Fields below `85%` or missing are visually marked and editable.
- Reviewer can edit values, then choose `Approve corrected details` or `Reject document`.
- Approval records reviewer action and changes the provenance to `human-approved`.
- Rejection does not save income and offers a new upload.

## Screen 2: voice application

### Ready state

- Central microphone control using a familiar mic icon and `Start call` label.
- Text-input fallback is available but visually secondary.
- Case context shows that income is already verified.
- The advisor summary pane is collapsed until relevant data exists.

### DigitalD modal

- Fictional DigitalD name is prominent with `Demo identity check` clearly visible.
- Show Emma Lindberg and the requested action `Identify for Bank Alfa session`.
- Commands: `Approve` and `Decline`.
- Never imitate a real identity provider or request credentials, passcodes, or biometrics.

### Active call

- Stable call controls: mute, end call, and text fallback.
- Audio state uses icon plus text: listening, Emma speaking, Bank Alfa speaking, processing.
- Transcript is readable but secondary to the voice state; final turns only are retained in the main transcript.
- When barge-in occurs, agent playback stops and a brief `Interrupted` state appears without resizing the layout.

### Consent affordances

Consent is primarily conversational, but the UI mirrors it:

- Credit check: requested, granted, denied, or consumed.
- Card block: requested for Mastercard 4471, granted, denied, or consumed.
- The customer does not click a separate approval button for these; the explicit spoken “yes” is captured as a consent event.
- DigitalD remains a modal approval because it simulates an external identity handoff.

## Screen 3: advisor summary

Shown in the same application, not a separate product.

Sections:

- Customer and identification status
- Verified income and provenance
- Property, deposit, and requested mortgage
- Credit result and existing car loan
- LTV, debt ratio, amortization, stressed-rate KALP, and monthly surplus
- Meeting booking
- Card incident outcome
- Caveats and missing evidence

The status must read `Preliminary assessment: looks supportable` and `Final decision: advisor required`. Never use `Approved` for the mortgage.

## Under-the-hood panel

The panel is a chronological timeline optimized for scanning during a presentation.

Each row has fixed columns:

- status icon
- short operation label
- state: queued, running, completed, blocked, review, or failed
- timestamp

Examples:

- `Content Understanding · Extract payslip · Completed`
- `Consent · Credit check · Granted`
- `Tool · Run credit check · Completed`
- `Tool · Calculate borrowing capacity · Completed`
- `Handoff · Advisor final decision · Required`
- `Consent · Block Mastercard 4471 · Granted`

The chosen scope is status-only. Do not show raw payloads, chain-of-thought, hidden prompts, credentials, or full customer records. A small service tag may identify `Content Understanding`, `Voice Live`, `Mock CRM`, or `Mock Cards`.

## Visual tokens

Recommended starting tokens, subject to accessibility verification:

| Token | Purpose | Suggested value |
|---|---|---|
| Ink | Primary text | `#172126` |
| Canvas | App background | `#F4F6F5` |
| Surface | Controls and repeated items | `#FFFFFF` |
| Alfa red | Brand/action accent | `#C9343A` |
| Verified teal | Success and verified state | `#087F78` |
| Review amber | Human review | `#B7791F` |
| Danger | Blocked/error | `#B42318` |
| Border | Structure | `#D5DCDA` |

Use an expressive but highly legible sans-serif available through a permitted web-font package, with a robust fallback. Do not default to Inter, Roboto, Arial, or a generic system-only treatment. Letter spacing is `0`.

## Motion

- One restrained stagger when the app first loads.
- Timeline rows enter as operations begin.
- Running operations may use a subtle progress indicator.
- No decorative looping motion.
- Respect `prefers-reduced-motion`.
- Audio visualization must not cause layout shifts.

## Accessibility

- WCAG AA color contrast for text and interactive states.
- Keyboard operation for upload, samples, review fields, modal, call controls, and reset.
- Visible focus indicators.
- Status is conveyed by icon/text, never color alone.
- Transcript updates use a non-disruptive live region.
- Modal focus is trapped and restored correctly.
- Tooltips name unfamiliar icon-only controls.

## Content style

- Customer copy is plain English and avoids internal lending jargon.
- Technical service names appear only in the under-the-hood panel.
- Currency uses `SEK 5,250,000` in UI and natural phrasing in speech.
- Dates use `21 September 2026`; times use `15:00`.
- Always say `preliminary assessment`, never `loan approval`.
