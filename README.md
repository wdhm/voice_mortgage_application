# Bank Alfa Mortgage AI Demo

Planning repository for a sales demo that shows how Microsoft Foundry can power a multimodal banking journey: payslip extraction with Azure Content Understanding, followed by a real-time mortgage and card-service conversation with Voice Live.

No application code has been created yet. The documents in this repository are the implementation brief for a future build agent.

## Demo at a glance

- Fictional bank: **Bank Alfa**
- Fictional customer: **Emma Lindberg**, a single salaried applicant
- Audience: mixed business and technical audience
- Target duration: 15 minutes
- Customer and agent language: English
- Hosting target: one Azure Container App
- AI platform: Microsoft Foundry
- Application stack: React/TypeScript frontend and Python/FastAPI backend
- State: in-memory demo data with a one-click reset
- Authentication: no application login; DigitalD is a simulated identity step inside the story

## Narrative

1. Emma uploads a Swedish payslip. Content Understanding extracts employer, gross salary, net salary, employment type, and pay date with field-level confidence.
2. A high-confidence result is saved to Emma's mock mortgage case. A low-confidence result is routed to an editable human-review state.
3. Emma starts a Voice Live call, completes a simulated DigitalD identification, and requests a mortgage pre-approval for a SEK 7,000,000 house in Täby with a SEK 1,750,000 deposit.
4. After explicit consent, the agent runs a mock credit check and deterministic borrowing-capacity calculation.
5. The agent gives a preliminary positive result, creates an advisor summary, adapts to Emma being away for three weeks, and books Monday, 21 September 2026 at 15:00.
6. Emma reports a stolen card. The agent finds Mastercard 4471, asks for explicit final confirmation, blocks it, and orders a replacement.
7. The UI makes human responsibility explicit: an advisor reviews uncertain documents and makes the final lending decision.

## Documentation

- [Business case and demo script](docs/business-case-and-demo-script.md)
- [Architecture and integrations](docs/architecture.md)
- [UX and design specification](docs/ux-design.md)
- [Functional specification](docs/functional-specification.md)
- [Implementation plan and acceptance tests](docs/implementation-plan.md)

## Scope boundaries

This is a demo, not a production banking system. CRM, credit, mortgage policy, calendar, card processing, DigitalD, and advisor workflows use realistic fake data and deterministic mock behavior. No real customer data, identity provider, credit bureau, calendar, core banking system, or card network is integrated.

“Powered by Microsoft Foundry” means the model, Voice Live experience, Content Understanding analyzer, agent/tool interaction, and AI observability use Foundry capabilities. The web application itself is hosted on Azure Container Apps.

## Reference implementation

The design was informed by `~/repos/voice-live-api-assistant`. Useful patterns retained from that project are:

- Python and FastAPI for session and tool orchestration
- A realtime event stream that drives a visible action panel
- A registry of explicit tool schemas and deterministic mock functions
- In-memory demo state and a reset operation
- Voice Live session events for transcripts, audio, tool calls, and interruption handling

Patterns intentionally changed:

- React replaces Streamlit for stronger presentation control and browser audio support.
- Browser microphone capture replaces server-attached PyAudio because the app runs in Azure Container Apps.
- WebSocket is used for duplex browser audio and live events; SSE is not sufficient for upstream audio.
- One Voice Live agent calls domain tools directly. The reference repository defines specialist Agent Framework agents, but its active Voice Live path registers the underlying Python functions directly.
- Barge-in is an explicit tested behavior. The reference combines disabled semantic-VAD interruption with manual response cancellation, so its behavior should not be copied without verification.

## Handoff rule

The future build agent must read all documents before generating code. Where an SDK or API has changed since this plan was written, it must preserve the specified behavior and update the implementation to the current stable service contract. It must not silently weaken consent gates, human review, barge-in, trace visibility, or deterministic demo reset behavior.
