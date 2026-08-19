# Business Case and Demo Script

## Executive proposition

Bank Alfa wants to reduce effort in common mortgage journeys without hiding automation from customers or advisors. The demo shows one coherent interaction in which AI reads an income document, holds a natural voice conversation, calls business tools, adapts to new information, and hands consequential decisions to a person.

The sales message is not “AI replaces an advisor.” It is “Microsoft Foundry lets the bank combine multimodal understanding, realtime conversation, governed actions, and observable human handoffs on one AI platform.”

## Business outcomes

- Reduce manual entry of income details.
- Ask customers only for information that is still missing.
- Resolve multiple intents in one conversation without forcing channel changes.
- Require explicit customer consent before sensitive actions.
- Give advisors a structured case summary instead of an unstructured call transcript.
- Route uncertain extraction to review rather than treating model output as fact.
- Make tool use and controls visible enough for a mixed business and technical audience.

## Audience and format

- Audience: bank executives, product owners, architects, and engineers
- Duration: 15 minutes
- Presentation mode: live, in English
- Intended order: Part 1, pause, then Part 2
- Independence: either part can be reset and demonstrated separately

## Fictional scenario

Emma Lindberg is permanently employed by Northstar AB and wants to buy a house in Täby for approximately SEK 7,000,000. She has SEK 1,750,000 available as a deposit and an existing car loan. Bank Alfa already has a customer record for her, but it needs current income evidence.

All people, institutions, records, scores, accounts, documents, and transactions are fictional. DigitalD is an invented identity provider and must never be presented as a real company.

## Canonical demo data

| Item | Demo value |
|---|---:|
| Customer | Emma Lindberg |
| Employer | Northstar AB |
| Employment | Permanent, full-time |
| Gross monthly salary | SEK 96,000 |
| Net monthly salary | SEK 62,400 |
| Pay date | 25 August 2026 |
| Property location | Täby |
| Purchase price | SEK 7,000,000 |
| Deposit | SEK 1,750,000 |
| Requested mortgage | SEK 5,250,000 |
| Existing car-loan balance | SEK 180,000 |
| Existing car-loan payment | SEK 4,200/month |
| Mock internal credit score | 781/999, low risk |
| Card to block | Bank Alfa Mastercard ending 4471 |
| Meeting | Monday, 21 September 2026 at 15:00 |

The mortgage assumptions are illustrative demo policy, not financial advice or a representation of any real bank's underwriting rules.

## Presenter script

### Opening: 45 seconds

1. Introduce Bank Alfa and Emma.
2. State that all operational systems are mocked, while the AI capabilities use Microsoft Foundry.
3. Point out the fixed split screen: customer journey on the left, live AI activity on the right.
4. Explain that the final mortgage decision remains with an advisor.

### Part 1: payslip understanding, 3 minutes

1. Open the Income Document step.
2. Upload the bundled high-confidence Swedish payslip or choose it from the sample selector.
3. While analysis runs, point to `Content Understanding` in the activity panel.
4. Show each extracted field, its confidence, and its source highlight:
   - Northstar AB
   - SEK 96,000 gross
   - SEK 62,400 net
   - Permanent, full-time
   - 25 August 2026
5. Show that all required fields meet the `0.85` threshold and are saved to the mortgage case.
6. Briefly switch to the bundled low-confidence sample, or reset and upload it, to show the review path.
7. Correct one uncertain field, approve the extraction as the human reviewer, and point out that automation pauses until approval.
8. Reset to the canonical high-confidence case before Part 2.

### Pause: 15 seconds

State that Part 1 and Part 2 are independently runnable, but the verified income now becomes context for the call so Emma is not asked for it again.

### Part 2: Voice Live conversation, 8 minutes

The wording may vary naturally. The behavioral beats must remain stable.

1. Presenter starts the voice session.
2. Agent: “Welcome to Bank Alfa. Before we begin, please approve the DigitalD identification request on screen.”
3. Presenter approves the fictional DigitalD modal.
4. The agent calls `get_crm_profile`; the UI reveals Emma's profile and existing car loan.
5. Emma: “I want a mortgage pre-approval for a house in Täby. It costs around seven million kronor.”
6. Agent recognizes that verified income is already in the case and asks for consent to run a credit check.
7. Emma: “Yes, you can run it.”
8. The consent event changes to granted, then `run_credit_check` executes.
9. Agent asks only for the missing deposit.
10. Emma: “I have one million seven hundred and fifty thousand kronor.”
11. The agent calls `calculate_borrowing_capacity`, explains the preliminary result in plain language, and calls `write_advisor_summary`.
12. Agent: “The numbers look like they hold for a preliminary assessment. An advisor still needs to make the final decision.”
13. The agent offers near-term meeting times.
14. Emma: “I am away for three weeks. Do you have anything after that?”
15. The agent calls `get_available_meeting_times` again with a later date constraint.
16. Emma selects Monday, 21 September at 15:00; `book_meeting` completes.
17. Before ending, Emma says: “One more thing. My card was stolen.”
18. The agent calls `get_customer_cards`, identifies Mastercard 4471, and asks: “Should I block Mastercard ending 4471 and order a replacement now?”
19. Emma: “Yes, do that.”
20. Only after the explicit confirmation event does `block_card_and_order_replacement` run.
21. Agent confirms the block, replacement order, meeting, and advisor handoff, then says goodbye.

### Barge-in moment

At one safe point, interrupt the agent while it is speaking, for example while it lists meeting times. The current audio must stop promptly, the interruption must appear in the event panel, and the agent must respond to the new utterance without losing case context.

### Technical close: 2 minutes

1. Recap the Foundry services: Voice Live, realtime model/agent tool calling, Content Understanding, and Foundry/Application Insights tracing.
2. Show that the right panel displays application-safe activity, while detailed platform traces remain available in Foundry.
3. Reiterate the two human controls: low-confidence document review and advisor-owned final lending decision.
4. Reset the demo to prove that no real backend system was changed.

## Objection handling

| Audience question | Suggested response |
|---|---|
| Is DigitalD real? | No. It is deliberately fictional and simulates an identity handoff. |
| Is this making a lending decision? | No. It produces an illustrative preliminary calculation and advisor summary. The advisor owns the final decision. |
| Are the integrations real? | The AI services are real. CRM, credit, policy, calendar, and cards are deterministic mocks. |
| Can the model block a card without permission? | No. The tool dispatcher rejects the action unless explicit confirmation is recorded for the selected card and current session. |
| Can low-confidence OCR silently enter the case? | No. Any required field below 0.85 routes the document to editable human review. |
| Why show tool activity but not model reasoning? | Tool inputs, statuses, and business outputs are auditable. Private chain-of-thought is neither required nor appropriate to display. |

## Demo success criteria

- The audience sees one connected story, not a collection of AI features.
- Emma is never asked to repeat income already accepted from Part 1.
- The agent adapts to the three-week scheduling objection.
- Mortgage and stolen-card intents complete in one call.
- Credit and card tools cannot run before their respective consent gates.
- At least one human handoff is visible even if the happy path is used.
- Every completed tool call appears in the under-the-hood panel.
