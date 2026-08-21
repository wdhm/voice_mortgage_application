export type TranscriptTurn = { speaker: "customer" | "assistant"; text: string };

export type CustomerCase = {
  customer_name: string;
  identity_status: "not_identified" | "identified" | "declined";
  document: { name: string | null; status: string };
  transcript: TranscriptTurn[];
  meeting: null | {
    starts_at: string;
    ends_at: string;
    timezone: string;
    booking_reference: string;
  };
  card: null | {
    card_type: string;
    last_four: string;
    status: string;
    replacement_ordered: boolean;
  };
};

export type ExtractedField = {
  value: string | number | null;
  confidence: number | null;
  grounding: string | null;
  provenance: string;
  original_value: string | number | null;
};

export type ServiceCase = {
  customer_profile: {
    display_name: string;
    city: string;
    relationship_since: number;
    contact_summary: string;
    car_loan_balance: number;
    car_loan_payment: number;
  };
  identity_status: string;
  document_name: string | null;
  document_status: string;
  extracted_income: null | Record<string, ExtractedField>;
  accepted_income: null | Record<string, string | number>;
  credit_result: null | Record<string, string | number>;
  capacity_result: null | Record<string, string | number | boolean | string[]>;
  advisor_summary: null | Record<string, unknown>;
  booked_meeting: null | { starts_at: string; booking_reference: string };
  cards: Array<{ card_type: string; last_four: string; status: string }>;
  replacement_order: null | { order_reference: string; delivery_estimate: string };
  events: Array<{
    event_id: string;
    timestamp: string;
    display: { label: string; status: string; service: string };
  }>;
};