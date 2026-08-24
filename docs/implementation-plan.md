# Implementation Plan and Acceptance Tests

## Build principles

- Read all planning documents before scaffolding.
- Preserve the behavioral contracts even if current SDK names differ.
- Use current stable Azure SDK/API versions where available; pin versions after a working spike.
- Keep mocks deterministic and AI behavior bounded by server-side validation.
- Build the presentation path first, then harden failure paths.
- Do not add real banking integrations.

## Proposed repository shape

This is a target, not code created in the planning phase.

```text
voice_mortgage_application/
  README.md
  docs/
  app/
    api/
    domain/
    tools/
    voice/
    documents/
    telemetry/
    static/
  web/
    src/
  tests/
    unit/
    integration/
    e2e/
  demo-assets/
  infra/
  azure.yaml
  pyproject.toml
  package.json
```

## Phase 0: technical spikes

Time-box these before committing to SDK details.

1. Connect from FastAPI to the existing Foundry resource with managed identity or developer credentials.
2. Establish a Voice Live session and relay browser microphone/audio with measurable barge-in.
3. Verify current Voice Live tool-call event shapes and response cancellation/truncation behavior.
4. Create a Content Understanding payslip analyzer with field confidence and source grounding enabled.
5. Confirm OpenTelemetry traces appear in the existing Foundry project's trace view through Application Insights.
6. Verify one Azure Container App can serve React assets, REST, and the application WebSocket.

Exit criterion: each spike has a short recorded result in the repository, including selected API versions and any deviation from this architecture.

## Phase 1: domain state and deterministic tools

1. Define typed `DemoCase`, consent, event, income, credit, capacity, meeting, card, and summary models.
2. Implement canonical Emma Lindberg fixture and reset behavior.
3. Implement tool functions and server-side guards.
4. Implement the deterministic mortgage calculation with a golden test for every intermediate value.
5. Implement idempotency for booking and card replacement.

Exit criterion: all tools pass unit tests without Voice Live or Azure access.

## Phase 2: Content Understanding flow

1. Define the custom payslip analyzer schema.
2. Create fake high- and low-confidence Swedish payslip assets with no real personal data.
3. Implement upload validation and analysis polling.
4. Map service output into the domain schema, retaining field confidence and grounding.
5. Implement automatic acceptance and editable human review.

Exit criterion: both bundled documents reliably reach their intended terminal states, and approved income is reusable by the case.

## Phase 3: Voice Live flow

1. Implement the single Voice Live agent instructions and explicit function schemas.
2. Implement browser microphone capture, server relay, and audio playback.
3. Implement final transcript events and text-input fallback.
4. Implement DigitalD modal handoff.
5. Implement consent extraction and dispatcher enforcement.
6. Implement barge-in, cancellation, and audio-queue clearing.
7. Run the complete mortgage, rescheduling, and stolen-card script.

Exit criterion: the canonical 20-beat conversation completes without manual state edits and a protected action cannot be forced through prompt wording alone.

## Phase 4: presentation UI

1. Build the fixed customer/under-the-hood split.
2. Build document empty, analyzing, accepted, review, rejected, and failed states.
3. Build voice ready, identifying, active, interrupted, reconnecting, and ended states.
4. Build the status-only operation timeline.
5. Build the same-screen advisor summary.
6. Add reset confirmation, responsive tabs, accessibility, and reduced motion.

Exit criterion: Playwright screenshots at desktop and mobile viewports show no overlap, clipping, blank media, or layout shifts during dynamic updates.

## Phase 5: telemetry and Azure packaging

1. Add OpenTelemetry spans and correlation across document, voice, and tool operations.
2. Sanitize visible events and disable trace content capture by default.
3. Build one production container that serves API and compiled frontend.
4. Add Azure Developer CLI configuration and Bicep for Container Apps hosting, registry, identity, and telemetry connections while referencing the existing Foundry project.
5. Configure one minimum and maximum replica for in-memory-state correctness.
6. Add health/readiness checks and deployment smoke tests.

Exit criterion: deployed demo completes both parts from a browser over HTTPS and its platform traces are discoverable by correlation ID.

## Phase 6: rehearsal hardening

1. Run the 15-minute script repeatedly from reset.
2. Test poor microphone input, interruption, reconnect, denied consent, and tool failures.
3. Tune prompts and VAD against measured behavior, not intuition.
4. Confirm all visible names and data are fictional.
5. Prepare a presenter runbook with resource checks, reset steps, and text fallback.

## Acceptance tests

### Document happy path

- Given the bundled high-confidence payslip, when it is analyzed, then all five required fields are returned with confidence at or above `0.85`.
- Accepted income exactly matches the canonical values and is available to the mortgage case.
- Selecting each field reveals source grounding where the service returns it.
- The timeline shows queued/running/completed states for Content Understanding.

### Document review path

- Given the bundled low-confidence payslip, at least one required field is below `0.85` or missing.
- No income is accepted before review.
- A reviewer can edit the uncertain value and approve it.
- Original extraction and human-approved value remain distinguishable in state.
- Rejecting the document leaves Part 2 without accepted income.

### Identity and privacy

- CRM details are not visible before DigitalD approval.
- Declining DigitalD prevents CRM and protected-tool access.
- No real identity-provider branding, credential request, or customer data appears.

### Mortgage conversation

- The agent retrieves CRM data and recognizes the existing car loan.
- The agent never asks for income when Part 1 has accepted it.
- The credit-check tool cannot execute before explicit consent.
- “Maybe,” silence, or a topic change does not grant credit consent.
- The agent asks for the missing deposit and accepts SEK 1,750,000.
- The deterministic tool returns 75% LTV, 4.71× debt ratio, 3% amortization, and approximately SEK 5,138 monthly KALP surplus.
- The spoken result is preliminary and keeps the advisor as final decision-maker.
- The advisor summary contains inputs, provenance, metrics, caveats, and handoff status.

### Scheduling objection

- Initial meeting slots are too early for Emma's stated constraint.
- “I am away for three weeks” causes a second availability call with a later earliest date.
- Monday, 21 September 2026 at 15:00 can be selected and booked.
- Repeating the booking call does not create a duplicate meeting.

### Card intent and authorization

- The same voice session can move from mortgage to stolen card without reset.
- Only safe card descriptors are returned.
- The agent matches Mastercard 4471 from the customer's stated last four digits.
- The customer's explicit request to block that card is sufficient authorization; no second confirmation is requested.
- A request for another or unknown card cannot authorize blocking 4471.
- The card tool blocks 4471 and creates one replacement order idempotently.
- The closing response accurately summarizes both completed errands.

### Barge-in

- While agent audio is playing, user speech stops playback promptly.
- Pending agent audio is cleared rather than played after the user finishes.
- An interruption event appears in the timeline.
- The next response addresses the interrupting utterance and preserves case context.
- The test records interruption latency; the team sets a numeric pass threshold after the Phase 0 spike on the target network.

### Trace and activity visibility

- Every tool call emits queued, running, and terminal events in order.
- Consent and human handoff events are visible independently of the transcript.
- The activity panel shows no chain-of-thought, prompt text, credential, raw document, or full card number.
- Tool and AI operations share correlation IDs with Application Insights spans.
- At least one complete run is discoverable in Foundry Traces.

### Reset and isolation

- Reset stops an active call and clears browser audio.
- Reset removes accepted income, consent, credit, calculation, meeting, block, replacement, summary, transcript, and event history.
- Reset restores Mastercard 4471 to active.
- Container restart does not recover prior demo state.
- Azure Container Apps runs exactly one active replica for this version.

### Accessibility and responsive UI

- All workflows are keyboard operable except speaking into the microphone.
- Focus is correctly managed around DigitalD and reset modals.
- Status never relies on color alone.
- No overlap or horizontal overflow occurs at 360px, 768px, 1440px, and a 16:9 presentation viewport.
- Reduced-motion mode removes nonessential animation.

## Definition of done

- Both parts run independently and in the canonical sequence.
- The live demo consistently completes in 15 minutes.
- All acceptance tests pass in the deployed Container App.
- Current API/SDK versions, model deployment, voice, required roles, and environment variables are documented without secret values.
- A clean deployment can target an existing Foundry project.
- The repository contains no real PII, banking credentials, or production endpoints.
- The presenter runbook includes preflight, reset, text fallback, and post-demo cleanup.

## Deferred implementation decisions

These are deliberately left for Phase 0 evidence rather than guessed in planning:

- exact Voice Live API and SDK version
- WebSocket proxy versus Voice Live WebRTC media path
- browser audio encoding and worklet implementation
- exact English voice and VAD parameters
- analyzer API version and whether labeled samples are needed to force repeatable confidence outcomes
- numeric barge-in latency threshold on the target presentation network
- exact existing Foundry project identifiers and Azure region
