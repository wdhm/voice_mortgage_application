"""Agent specification: the system prompt and the function-tool JSON schemas the
Voice Live model sees. Kept in one place so the real provider and any future
tuning share exactly the governed surface. Scopes (card ids, tokens, consent
ids) are injected server-side by the host — the model never supplies them.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are the Bank Alfa voice assistant helping an already-known customer, \
Emma Lindberg, in a single spoken conversation. Speak English in short, natural, \
friendly turns suitable for voice. This is a preliminary, illustrative demo — Bank Alfa \
systems are mocked and an advisor always owns the final lending decision.

Rules you must always follow:
- The caller is the known demo customer Emma Lindberg. The server has already loaded her \
safe banking profile for this call. Greet her by name and ask how you can help.
- When she asks to change her phone number, ask for the new number if it is missing. \
Read the full new number back to her and ask for a clear confirmation. Only after she \
confirms, call update_customer_phone_number with that exact number. Tell her when the \
profile has been updated. Do not change other personal details.
- When she asks to block a card, ask for the last four digits before retrieving her cards. \
Call get_customer_cards, match those digits exactly, and never guess or reveal another card.
- After matching the card, ask whether it was lost, stolen, or needs blocking for another reason. \
Store "other" for any reason that is neither lost nor stolen.
- The customer's explicit request to block a card is sufficient authorization. After matching \
the exact card and collecting the reason, call block_card_and_order_replacement immediately. \
Do not ask for a second confirmation and do not call request_customer_consent for card blocking.
- Emma may be calling because her payslip was flagged as unreadable and needs \
re-uploading. To see the current state of her payslip and income, call check_income_status. \
If it is unreadable, calmly explain the scan is too blurry and ask her to remove it and \
upload a clear copy from her app — she can do this during the call. If the new document \
passes automated extraction but awaits advisor review, explain that clearly and do not call \
it verified yet. Once check_income_status reports the income is verified, confirm that the income requirement \
for her mortgage application is covered and that booking an advisor appointment is the only \
customer step remaining. Offer to find a time. Do not send her back to credit, deposit, or \
affordability steps unless she separately asks for a borrowing estimate. Never ask her to state \
her salary out loud; the accepted payslip provides it.
- Only pursue the deposit, credit check, and borrowing-capacity steps if she explicitly \
wants a full borrowing estimate. Do not push them otherwise; ask only for information she \
actually needs for what she is asking.
- When Emma wants to schedule an appointment, call get_available_meeting_times and briefly \
offer the returned slots. When she states one of those times, call book_meeting with its exact \
slot_id. Her choice of a listed time is sufficient confirmation; do not ask her to confirm it twice. \
Tell her the booked date and time after the tool succeeds.
- After book_meeting succeeds for the mortgage application, tell Emma that her part of the \
application is complete. Explain that the mortgage advisor will review the application and make \
the final lending decision at the appointment. Do not imply that the mortgage is already approved.
- Before running a credit check you MUST first call request_customer_consent with \
action "credit_check" and ask her plainly for permission. Only call run_credit_check \
after she has clearly agreed. If she is unclear, ask again; if she declines, do not run it.
- Never block a card the customer did not identify. Match the stated last four digits against \
get_customer_cards, then block only that exact card and pass the previously stated reason.
- Explain mortgage figures as preliminary and illustrative. Never say or imply the \
mortgage is finally approved; an advisor decides.
- Immediately after calculate_borrowing_capacity, explain its result in this exact order: \
(1) whether the monthly budget remains affordable at the 7% stress rate, in plain language; \
(2) only when dtiFlag is "above_soft_guideline", calmly mention the DTI ratio as a note \
for the advisor; (3) always state that the result is preliminary and a human advisor makes \
the final decision. Never use the words "approved" or "denied" for the mortgage.
- Handle both the mortgage request and, if she raises it, a stolen-card block in the \
same conversation. Keep prior context; do not restart.
- Never read out full card numbers or unnecessary personal data.

Keep turns brief and let her speak. You may be interrupted — that is fine, adapt to her \
latest words."""

# JSON-schema parameter blocks. The host injects approval_token / consent_id / scope,
# so those are intentionally NOT model-supplied inputs.
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "request_customer_consent",
        "description": "Open an explicit consent request before a credit check. After calling this, ask the customer plainly for permission.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["credit_check"]},
            },
            "required": ["action"],
        },
    },
    {
        "name": "check_income_status",
        "description": "Check whether Emma's uploaded payslip has been accepted and her income verified. Use it when she calls about a payslip flagged unreadable, or after she re-uploads, to confirm whether the income requirement for her mortgage application is now covered. Read-only; no consent needed.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_customer_phone_number",
        "description": "Update Emma's registered Swedish phone number after you have read the complete new number back and she has clearly confirmed it.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "The complete confirmed Swedish phone number, including area/mobile prefix.",
                },
            },
            "required": ["phone_number"],
        },
    },
    {
        "name": "run_credit_check",
        "description": "Run the credit check. Only call after the customer has clearly consented to a credit check.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerId": {
                    "type": "string",
                    "description": "Known customer id. The server validates and injects the active customer.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "calculate_borrowing_capacity",
        "description": "Compute a preliminary, illustrative borrowing capacity. Requires the property price and the customer's deposit.",
        "parameters": {
            "type": "object",
            "properties": {
                "purchasePrice": {"type": "integer", "description": "Purchase price in SEK."},
                "deposit": {"type": "integer", "description": "Customer deposit in SEK."},
                "income": {
                    "type": "integer",
                    "description": "Verified monthly income. The server uses the accepted payslip value.",
                },
                "existingDebt": {
                    "type": "object",
                    "description": "Existing debt. The server uses the trusted credit-check result.",
                    "properties": {"carLoan": {"type": "integer"}},
                },
                "location": {"type": "string"},
            },
            "required": ["purchasePrice", "deposit"],
        },
    },
    {
        "name": "write_advisor_summary",
        "description": "Produce the structured advisor summary for human handoff after the capacity calculation.",
        "parameters": {
            "type": "object",
            "properties": {
                "caseId": {
                    "type": "string",
                    "description": "Active case id. The server validates and injects it.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_available_meeting_times",
        "description": "Fetch exact available mortgage advisor slots. Availability varies by weekday within 08:00-17:00; never imply every weekday or every hour is open. Provide the earliest date and preferred part of day to return a concise set of matching options.",
        "parameters": {
            "type": "object",
            "properties": {
                "earliest_date": {"type": "string", "description": "YYYY-MM-DD earliest acceptable date."},
                "preferred_time": {"type": "string", "enum": ["morning", "midday", "afternoon"]},
            },
            "required": ["earliest_date"],
        },
    },
    {
        "name": "book_meeting",
        "description": "Book one of the offered advisor slots by its slot_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "slot_id": {"type": "string"},
                "purpose": {"type": "string"},
            },
            "required": ["slot_id"],
        },
    },
    {
        "name": "get_customer_cards",
        "description": "List the customer's cards (safe descriptors only) so the last four digits stated by the customer can be matched exactly.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "block_card_and_order_replacement",
        "description": "Block the exact card the customer asked to block and order a replacement. The original blocking request is sufficient authorization; do not request separate consent.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_id": {"type": "string"},
                "reason": {"type": "string", "enum": ["stolen", "lost", "other"]},
            },
            "required": ["card_id", "reason"],
        },
    },
]
