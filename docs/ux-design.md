# UX and Design Specification

## Design intent

Bank Alfa should feel like a modern Nordic retail bank: clear, calm, trustworthy, and operational rather than promotional. The product has two distinct live work surfaces, not a landing page: a simple customer experience and a denser Bank Alfa employee service workspace.

The visual direction uses a bright neutral base, dark ink text, restrained red for Bank Alfa identity, teal for verified/completed states, amber for review, and red only for destructive or blocked states. Avoid a monochromatic blue banking template, oversized marketing headings, nested cards, decorative gradients, and excessive rounded pills.

## Experience model

The React application exposes two synchronized routes:

- `/customer`: used by Emma for payslip upload, customer-safe status, DigitalD, voice conversation, consent, and appointment confirmation.
- `/service`: used by the person working at Bank Alfa to see Emma's customer information, document extraction, confidence, review tasks, mortgage case, advisor summary, and AI actions.

They share a case but do not share a navigation shell or expose each other's controls. For the sales demo, open them in two browser windows side by side or on two displays.

## Customer desktop layout

The primary presentation viewport is a 16:9 laptop or projected display.

```text
+-----------------------------------------------------------------------+
| Bank Alfa                                    Help       Secure session |
+-----------------------------------------------------------------------+
| YOUR MORTGAGE APPLICATION                                           |
|                                                                     |
| 1 Income document        2 Conversation        3 Appointment         |
|                                                                     |
| Customer task: upload / status / voice conversation                 |
|                                                                     |
+-----------------------------------------------------------------------+
```

- The customer view uses the full width and keeps internal operations hidden.
- Header: compact, fixed height, with brand, help, and customer-safe connection status.
- Do not place the main experience inside a floating page card.

## Service desktop layout

```text
+-----------------------------------------------------------------------+
| Bank Alfa Service | Emma Lindberg | Case status | Reset | Connection  |
+----------------------+---------------------------+--------------------+
| CUSTOMER & CASE      | ACTIVE WORK               | AI ACTIVITY        |
| Identity and CRM     | Payslip review            | Tool status        |
| Existing products    | Mortgage calculations     | Consent events     |
| Contact summary      | Advisor summary           | Handoffs           |
|                      | Meeting and card outcome  | Service labels     |
+----------------------+---------------------------+--------------------+
```

- Customer/case rail: approximately 24% width.
- Active work area: approximately 48% width.
- AI activity timeline: approximately 28% width.
- The service view is denser and optimized for scanning, review, and repeated action.
- Repeated activity events may use compact cards with radius no greater than 8px.

## Mobile and narrow screens

The demo is optimized for desktop, but must remain functional on mobile.

- Each route remains a separate experience on mobile; there is no role-switch tab.
- The service workspace uses `Case`, `Review`, and `Activity` tabs at narrow widths.
- Voice controls remain reachable near the bottom safe area.
- Document fields stack without horizontal scrolling.
- No text, status, or button may overlap at 360px width.

## Global controls

- Bank Alfa wordmark: text treatment, not an imitation of a real bank.
- The customer side does not expose internal case identifiers or reset controls.
- Service-side case indicator: `Emma Lindberg · Mortgage application`.
- Service-side reset icon button with tooltip: requires confirmation if a session is active.
- Connection indicator: disconnected, connecting, ready, reconnecting, failed.
- Presenter mode is implicit; do not add explanatory feature copy to the live screen.

## Navigation and progress

The customer view uses a compact three-step control:

1. Income document
2. Voice application
3. Appointment

Completed steps show a check icon. A document under review uses a neutral pending icon rather than exposing an internal warning. The service view uses task-oriented navigation: `Overview`, `Income review`, `Mortgage`, `Cards`, and `AI activity`.

## Customer side: income document

### Empty state

- Large but restrained upload area for PDF, PNG, JPEG, and supported image formats.
- Upload button with file icon.
- A demo-only sample selector may provide `High-confidence payslip` and `Low-confidence payslip`; hide it in normal customer presentation mode.
- File constraints appear adjacent to the chooser, not as a feature tutorial.

### Analyzing state

- Uploaded document preview remains visible.
- A stable status area says the document is being reviewed without exposing the AI service or internal fields.
- Disable duplicate submission while analysis is active.

### Accepted state

- Confirmation strip: `Your income document has been received`.
- Do not show field confidence, source grounding, internal normalization, or review controls.
- Primary command: `Continue to voice application`.

### Review-required state

- Customer-safe banner: `Your document needs a manual review`.
- The customer can replace the uploaded document but cannot edit extracted bank records or approve their own evidence.
- Once the employee resolves the task, this status updates automatically.

## Service side: customer overview

- Show Emma's mock identity status, contact-safe profile, customer relationship, and existing car loan.
- Show accepted income and its provenance.
- Do not reveal full card numbers or unnecessary identity attributes.
- New customer and case events update without manual refresh.

## Service side: income review

- Two-column arrangement: document preview on the left, extracted fields on the right.
- Each field shows label, normalized value, confidence percentage, provenance, and review state.
- Selecting a field highlights its grounded source region where available.
- Fields below `85%` or missing are visually marked and editable.
- Employee commands: `Approve corrected details` and `Reject document`.
- Approval records the employee action and changes provenance to `human-approved`.

## Customer side: voice application

### Ready state

- Central microphone control using a familiar mic icon and `Start call` label.
- Text-input fallback is available but visually secondary.
- Customer-safe context shows that the income document has been received or reviewed.

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

- The customer sees the active credit-check or card-block request in plain language, not internal consent-state names.
- The customer does not click a separate approval button for these; the explicit spoken “yes” is captured as a consent event.
- DigitalD remains a modal approval because it simulates an external identity handoff.

## Service side: advisor summary

Shown only in the Bank Alfa service workspace.

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

## Service side: AI activity timeline

The timeline is a chronological service-side view optimized for scanning during a presentation.

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

The chosen activity scope is status-only. Customer information belongs in the case workspace, not duplicated inside activity rows. Do not show raw payloads, chain-of-thought, hidden prompts, credentials, or full customer records. A small service tag may identify `Content Understanding`, `Voice Live`, `Mock CRM`, or `Mock Cards`.

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
- Technical service names appear only in the service-side AI activity timeline.
- Currency uses `SEK 5,250,000` in UI and natural phrasing in speech.
- Dates use `21 September 2026`; times use `15:00`.
- Always say `preliminary assessment`, never `loan approval`.
