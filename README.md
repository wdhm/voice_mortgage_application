# Bank Alfa Mortgage AI Demo

Starter implementation for a sales demo that shows how Microsoft Foundry can power a multimodal banking journey: payslip extraction with Azure Content Understanding, followed by a real-time mortgage and card-service conversation with Voice Live.

The application uses Azure Voice Live for browser-based speech-to-speech conversation. Document extraction, CRM, credit, mortgage, calendar, and card operations remain deterministic demo adapters; Azure Content Understanding is configured but its runtime adapter is not implemented yet.

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
- Experiences: separate synchronized customer and bank-employee views

## Application sides

- **Customer side (`/customer`)**: Emma uploads her payslip, sees a simple processing outcome, completes DigitalD, and conducts the Voice Live conversation. It contains only customer-appropriate information.
- **Service side (`/service`)**: a Bank Alfa employee sees Emma's mock CRM profile, payslip extraction and confidence, review tasks, consent and tool activity, mortgage calculations, meeting, card status, and advisor summary.

Both routes are served by the same application and share the same in-memory demo case. They can be opened in separate browser windows during the presentation so the audience can see customer actions appear live in the employee workspace.

## Narrative

1. Emma uploads a Swedish payslip from the customer side. Content Understanding extracts employer, gross salary, net salary, employment type, and pay date with field-level confidence.
2. The service side receives the extraction. A high-confidence result is saved to Emma's mock mortgage case; a low-confidence result becomes an editable task for the bank employee.
3. Emma starts a Voice Live call, completes a simulated DigitalD identification, and requests a mortgage pre-approval for a SEK 7,000,000 house in Täby with a SEK 1,750,000 deposit.
4. After explicit consent, the agent runs a mock credit check and deterministic borrowing-capacity calculation.
5. The agent gives a preliminary positive result, creates an advisor summary, adapts to Emma being away for three weeks, and books Monday, 21 September 2026 at 15:00.
6. Emma reports a stolen card. The agent finds Mastercard 4471, asks for explicit final confirmation, blocks it, and orders a replacement.
7. The service side makes human responsibility explicit: a bank employee reviews uncertain documents and an advisor makes the final lending decision.

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

## Local development

Prerequisites: Python 3.12+ and Node.js 20+.

1. Create and activate a Python virtual environment, then install `requirements-dev.txt`.
2. Install the frontend dependencies from `web/package.json`.
3. Copy `.env.sample` to `.env`, run `az login --tenant cc48e4fe-6662-414d-aeff-4eb633735b38`, and ensure your user has Cognitive Services User and Foundry User on `foundry-mortgage`.
4. Start FastAPI from the repository root:

	```powershell
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload
	```

5. Start Vite from the `web` directory:

	```powershell
	npm run dev
	```

Open `http://localhost:5173/customer` and `http://localhost:5173/service` in separate browser windows. The frontend proxies API and WebSocket traffic to FastAPI.

For a production-style Python process after building the frontend, run `gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} main:app` in a compatible shell. FastAPI serves `web/dist` when that directory exists.

## Tests

- Backend: `pytest`
- Frontend: run `npm test` from `web`

Backend and frontend unit tests do not require Azure. Using the microphone requires Azure access and the Voice Live configuration in `.env`.

## Foundry integration baseline

- Voice Live uses `azure-ai-voicelive` `1.3.0` with API `2026-04-10` and the Foundry account endpoint.
- Content Understanding uses `azure-ai-contentunderstanding` `1.1.0` with GA API `2025-11-01` and the same account endpoint.
- Deployed code uses `DefaultAzureCredential` with the user-assigned identity selected by `AZURE_CLIENT_ID`.
- The identity needs `Cognitive Services User` and `Foundry User` on the Foundry account.
- The live realtime, completion, and embedding deployments are provisioned. Content Understanding analyzer and default-model mapping verification remains required before enabling the real document adapter.

See [.env.sample](.env.sample) for non-secret configuration names and [Architecture and integrations](docs/architecture.md#verified-foundry-contract) for endpoint and call details.
