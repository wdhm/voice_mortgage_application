# Architecture and Integrations

## Architecture goals

- Stay close to the reference application's Python/FastAPI, explicit-tool, realtime-event, and in-memory-state patterns.
- Support browser audio from an Azure-hosted application.
- Keep the demo in one deployable Container App.
- Use Microsoft Foundry for all AI capabilities.
- Keep mock banking behavior deterministic and testable.
- Separate audience-safe live activity from deeper platform telemetry.
<<<<<<< HEAD
- Provide distinct customer-facing and bank-employee service views over one shared case.
=======
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa

## Logical architecture

```mermaid
flowchart LR
<<<<<<< HEAD
    Customer[Customer view /customer] <-->|HTTPS and app WebSocket| API[FastAPI application]
    Employee[Service view /service] <-->|HTTPS and app WebSocket| API
=======
    Browser[React browser app] <-->|HTTPS and app WebSocket| API[FastAPI application]
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
    API <-->|Realtime WebSocket| VL[Foundry Voice Live]
    API --> CU[Content Understanding analyzer]
    API --> Tools[Deterministic mock tools]
    Tools --> State[In-memory demo case]
    API --> OTel[OpenTelemetry]
    OTel --> AppI[Application Insights]
    AppI --> Traces[Foundry Traces]
    API -. managed identity .-> VL
    API -. managed identity .-> CU
    ACA[Azure Container Apps] -. hosts .-> API
<<<<<<< HEAD
    API -. serves React routes .-> Customer
    API -. serves React routes .-> Employee
=======
    API -. serves static build .-> Browser
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
```

## Deployment shape

One Azure Container App hosts one container image:

- FastAPI is the single server process.
- FastAPI serves the compiled React static assets.
<<<<<<< HEAD
- React exposes `/customer` and `/service` as distinct role-oriented routes, not tabs that reveal the other role's data.
- REST endpoints handle upload, role-filtered case state, employee review actions, reset, and health.
- WebSocket connections subscribe with a role-specific event projection. The customer connection also carries browser audio; the service connection receives employee-safe case and activity updates.
=======
- REST endpoints handle upload, case state, review actions, reset, and health.
- One application WebSocket handles browser audio, transcript events, connection state, consent events, and tool activity.
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
- FastAPI opens a server-side Voice Live connection using managed identity. Foundry credentials and access tokens are never sent to the browser.

Azure Container Apps HTTP ingress supports TLS termination and WebSockets. Set a minimum replica count of one for presentation reliability. Because case state is process-local, the demo must use one active replica and no scale-out. A later production design would externalize session state.

<<<<<<< HEAD
## Verified Foundry contract

The August 2026 technical audit established this implementation baseline:

| Capability | Selected contract | Endpoint and call shape |
|---|---|---|
| Voice Live | Python SDK `azure-ai-voicelive` `1.3.0`; API `2026-04-10` | Account endpoint `https://<account>.services.ai.azure.com/`; the SDK opens `/voice-live/realtime` with `api-version` and deployment name in `model` |
| Content Understanding | Python SDK `azure-ai-contentunderstanding` `1.1.0`; GA API `2025-11-01` | Account endpoint; SDK `begin_analyze(analyzer_id=..., inputs=...)` returns a long-running poller |
| Authentication | `azure-identity` `1.25.3` and `DefaultAzureCredential` | User-assigned identity selected with `AZURE_CLIENT_ID`; Voice Live token scope is `https://ai.azure.com/.default` |
| Telemetry | `azure-monitor-opentelemetry` `1.8.9` | Application Insights connection string supplied only to the trusted backend |

The project endpoint (`.../api/projects/<project>`) is retained only for project-scoped Foundry APIs. It is not the base URL for Voice Live or Content Understanding. Client code must pass the configured account endpoint to the SDK and must not manually concatenate a WebSocket URL.

The live account has a succeeded `gpt-realtime-1.5` deployment (model version `2026-02-23`) and succeeded `gpt-5.2` and `text-embedding-3-large` deployments. Content Understanding uses resource-level defaults mapping its completion and embedding model names to those deployment names. The configured custom analyzer ID is `mortgage_payslip`.

=======
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
## Realtime voice flow

```mermaid
sequenceDiagram
<<<<<<< HEAD
    participant C as Customer view
    participant E as Service view
=======
    participant B as Browser
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
    participant A as FastAPI
    participant V as Voice Live
    participant T as Mock tool dispatcher
    participant S as Case state

<<<<<<< HEAD
    C->>A: Open customer WebSocket
    E->>A: Open service WebSocket
    A->>V: Open authenticated Voice Live session
    A->>V: Configure English voice, VAD, instructions, tools
    C->>A: PCM audio frames
    A->>V: Input audio events
    V-->>A: Speech, transcript, audio, and tool events
    A-->>C: Audio and customer-safe events
    A-->>E: Employee-safe case and activity events
=======
    B->>A: Open app WebSocket
    A->>V: Open authenticated Voice Live session
    A->>V: Configure English voice, VAD, instructions, tools
    B->>A: PCM audio frames
    A->>V: Input audio events
    V-->>A: Speech, transcript, audio, and tool events
    A-->>B: Audio and sanitized live events
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
    V->>A: Function call request
    A->>T: Validate schema and consent guard
    T->>S: Read or mutate mock case
    T-->>A: Structured result
    A->>V: Function result
<<<<<<< HEAD
    A-->>E: Tool status completed
=======
    A-->>B: Tool status completed
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
```

The implementation may use the current Voice Live browser-oriented WebRTC option if a short technical spike proves it simpler and equally secure. The behavioral contract remains: browser microphone, low latency, tool calls on the trusted server, no service credential in the browser, and observable barge-in. The default plan uses an application WebSocket proxy because it mirrors the reference backend-controlled session and tool registry.

## Barge-in contract

Barge-in is not an SDK-default assumption. It is an end-to-end behavior:

1. Voice activity begins while agent audio is playing.
2. Browser playback is stopped and queued audio is cleared.
3. The active Voice Live response is cancelled or truncated according to the current API contract.
4. An `interruption.detected` event is emitted to the UI.
5. New user audio is processed as the next turn without losing accepted case data or consent history.

The Voice Live session's VAD/interruption configuration and manual cancellation logic must agree. The implementation must not repeat the reference repository's contradictory combination of `interrupt_response=False` and manual cancellation without a verified reason.

## Document flow

```mermaid
sequenceDiagram
<<<<<<< HEAD
    participant U as Customer view
    participant E as Service view
    participant A as FastAPI
    participant C as Content Understanding
    participant R as Bank employee
    participant S as Case state

    U->>A: Upload image or PDF
=======
    participant B as Browser
    participant A as FastAPI
    participant C as Content Understanding
    participant R as Human reviewer
    participant S as Case state

    B->>A: Upload image or PDF
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
    A->>C: Analyze with payslip schema and confidence enabled
    C-->>A: Typed fields, confidence, and source grounding
    A->>A: Validate required fields and threshold
    alt all required fields >= 0.85
        A->>S: Save verified income
<<<<<<< HEAD
        A-->>U: Customer-safe accepted status
        A-->>E: Extraction details and accepted status
    else missing or low-confidence field
        A-->>U: Under review status
        A-->>E: Manual review task with extraction details
        R->>A: Edit and approve or reject
        A->>S: Save reviewer-approved income
        A-->>U: Updated customer-safe status
=======
        A-->>B: Accepted
    else missing or low-confidence field
        A-->>B: Manual review required
        R->>A: Edit and approve or reject
        A->>S: Save reviewer-approved income
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
    end
```

The custom Content Understanding schema uses direct extraction for employer, gross salary, net salary, employment type, and pay date. Confidence and source grounding must be enabled. Normalized values are retained alongside display values and provenance.

<<<<<<< HEAD
Analysis is asynchronous. The adapter submits binary content or an `AnalysisInput`, awaits the SDK poller, then maps typed field values, `confidence`, `spans`, and `source` grounding into the domain model. Analyzer creation belongs in setup tooling, not in the request path.

=======
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
## Foundry boundary

| Capability | Service or component | Real or mock |
|---|---|---|
| Document extraction | Azure Content Understanding in Foundry Tools | Real |
| Speech-to-speech session | Voice Live on a Foundry resource | Real |
| Realtime model and function selection | Voice Live model session | Real |
| Tool execution | FastAPI tool dispatcher | Deterministic mock |
| CRM, credit, policy, calendar, cards | In-memory adapters | Mock |
| AI tracing | OpenTelemetry to Application Insights and Foundry Traces | Real |
<<<<<<< HEAD
| Customer status updates | Minimal customer-safe application events | Real app telemetry |
| Employee AI activity timeline | Sanitized tool, consent, and handoff events | Real app telemetry |
=======
| Customer-facing activity panel | Sanitized application events | Real app telemetry |
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
| Identity approval | DigitalD modal and mock tool | Mock |

The Voice Live session is the single agent for this demo. Specialist Foundry agents are not required. This avoids duplicate orchestration layers and keeps realtime latency and tool ordering understandable.

## Event and observability model

<<<<<<< HEAD
Every operation receives a session ID, case ID, correlation ID, timestamp, and sequence number. Each browser receives a role-filtered event projection.
=======
Every operation receives a session ID, case ID, correlation ID, timestamp, and sequence number. The browser sees only a sanitized event projection.
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa

Event families:

- `session.*`: connecting, ready, stopped, failed
- `audio.*`: user speaking, assistant speaking, interruption detected
- `transcript.*`: final user and assistant text
- `document.*`: uploaded, analyzing, extracted, review required, approved, rejected
- `consent.*`: requested, granted, denied, consumed
- `tool.*`: queued, running, completed, failed, blocked by policy
- `case.*`: income saved, summary updated, reset
- `handoff.*`: document reviewer required, advisor final decision required

<<<<<<< HEAD
The customer view receives only statuses and information appropriate to Emma's journey. The service view shows tool name and status, customer case updates, consent, review, and handoff events. Neither view exposes chain-of-thought, credentials, or sensitive raw payloads.

## View authorization boundary

This sales demo has no real login, but the application must still enforce view separation in backend response models and event subscriptions:

- `/customer` can upload a document, control the voice session, respond to DigitalD, view customer-safe status, and read the conversation.
- `/service` can view the mock CRM profile, document and confidence details, review or reject extraction, view calculations, see tool activity, and read the advisor summary.
- Customer endpoints never return internal credit scores, confidence diagnostics, tool payloads, advisor notes, or unrelated CRM data.
- Service actions such as document approval are unavailable through customer endpoints even if a caller manually constructs a request.
- Because there is no production authentication, this is demo-grade role separation rather than a security claim. A production design would authenticate employees and authorize case access.
=======
The visible panel shows tool name and status, plus concise consent and handoff events. It does not expose chain-of-thought, credentials, full documents, or sensitive raw payloads.
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa

OpenTelemetry spans should cover document analysis, Voice Live session lifecycle, model responses where supported, and each tool invocation. Application Insights is connected to the existing Foundry project so traces can be viewed in Foundry. Content recording should be disabled by default even though data is fictional; enable it only as an explicit demo configuration.

## Identity and secrets

- Azure Container App uses a managed identity.
<<<<<<< HEAD
- Grant the managed identity `Cognitive Services User` and `Foundry User` at the existing Foundry account scope. The former covers Content Understanding data actions; current Voice Live guidance requires both roles.
=======
- Grant only the roles required to call the existing Foundry resource and emit telemetry.
>>>>>>> b277455e654930997abeecf56a0842d12faa0eaa
- Use `DefaultAzureCredential` in deployed code and developer credentials locally.
- Keep endpoints and non-secret deployment names in configuration.
- Keep any unavoidable secrets in Container Apps secrets or Key Vault references, never in source or browser bundles.
- DigitalD is not Azure authentication. It is a fictional business-flow mock.
- The demo URL has no app login by product decision; deployment documentation must call out that public exposure is acceptable only because all data is fake.

## State and concurrency

State is an in-memory `DemoCase` keyed by the current demo session. It contains document results, accepted income, identification state, CRM profile, consent records, calculation inputs/results, meeting, cards, advisor summary, and ordered events.

For the initial demo:

- one active demo session at a time
- one Container App replica
- reset restores the complete canonical state
- container restart loses all progress and returns to canonical state
- no database, cache, blob persistence, or customer PII

The implementation should isolate state behind a repository interface so persistence can be added later without changing tools.

## Reliability and fallback

- Text input can replace microphone input within the same active conversation.
- Voice WebSocket reconnect is visible and does not claim an action succeeded unless its tool completed.
- Tool functions are idempotent where practical; repeated booking or card-block calls return the existing result.
- Reset closes active voice sessions before restoring state.
- A health endpoint checks application readiness and configuration presence but does not leak endpoints or credentials.
- Curated high- and low-confidence payslips make both document paths repeatable.

## Reference differences to preserve

The reference repository uses FastAPI, Streamlit, SSE, PyAudio, an event-bus singleton, in-memory account state, and direct Voice Live function tools. This design keeps FastAPI, explicit tools, event-driven UI updates, and resettable memory state. It changes the UI and transport because a hosted browser cannot use the Container App's microphone. It also treats tool lifecycle events as first-class instead of inferring them only from domain mutations.

## Official references

- [Voice Live API overview](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live)
- [How to use Voice Live](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live-how-to)
- [Voice Live with WebRTC](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live-webrtc)
- [Content Understanding document solutions](https://learn.microsoft.com/azure/ai-services/content-understanding/document/overview)
- [Set up tracing in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup)
- [Azure Container Apps ingress and WebSocket support](https://learn.microsoft.com/azure/container-apps/ingress-overview)
