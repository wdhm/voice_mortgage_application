// Shared types + tiny API client for the demo backend.

export type EventStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "blocked"
  | "review"
  | "granted"
  | "denied"
  | "required"
  | "info";

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  session_id: string;
  case_id: string;
  correlation_id: string;
  sequence: number;
  epoch: number;
  timestamp: string;
  display: {
    label: string;
    status: EventStatus;
    service?: string | null;
  };
}

export interface Health {
  status: string;
  voice_provider: string;
  document_provider: string;
  foundry_configured: boolean;
  epoch: number;
}

export async function getHealth(): Promise<Health> {
  const r = await fetch("/api/health");
  return r.json();
}

export async function resetDemo(): Promise<{ status: string; epoch: number }> {
  const r = await fetch("/api/reset", { method: "POST" });
  return r.json();
}

export async function emitEcho(label: string): Promise<void> {
  await fetch("/api/echo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label }),
  });
}

// ---- Documents (Screen 1) ---------------------------------------------- //

export type DocumentState =
  | "empty"
  | "analyzing"
  | "accepted_automatically"
  | "review_required"
  | "accepted_after_review"
  | "rejected_by_reviewer"
  | "analysis_failed";

export interface ExtractionField {
  value: string | null;
  normalized_value: number | string | null;
  confidence: number | null;
  provenance: string;
  source_grounding: string | null;
  original_value: string | null;
  passes: boolean;
}

export type FieldName =
  | "employer_name"
  | "gross_salary_monthly"
  | "net_salary_monthly"
  | "employment_type"
  | "pay_date";

export interface DocumentProjection {
  document_state: DocumentState;
  provider: string;
  threshold: number;
  uploaded_document: {
    filename: string;
    content_type: string;
    sample_key: string | null;
    uploaded_at: string;
  } | null;
  fields: Record<FieldName, ExtractionField> | null;
  accepted_income: Record<string, unknown> | null;
  review_record: { edited_fields: string[]; decision: string | null } | null;
}

export interface SampleMeta {
  key: string;
  label: string;
  description: string;
}

export async function listSamples(): Promise<SampleMeta[]> {
  const r = await fetch("/api/documents/samples");
  return r.json();
}

export async function getDocumentState(): Promise<DocumentProjection> {
  const r = await fetch("/api/documents/state");
  return r.json();
}

export async function analyzeSample(sampleKey: string): Promise<DocumentProjection> {
  const r = await fetch("/api/documents/analyze-sample", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sample_key: sampleKey }),
  });
  return r.json();
}

export async function uploadDocument(file: File): Promise<DocumentProjection> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch("/api/documents/upload", { method: "POST", body: form });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Upload failed");
  return r.json();
}

export async function removeDocument(): Promise<DocumentProjection> {
  const r = await fetch("/api/documents/upload", { method: "DELETE" });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Remove failed");
  return r.json();
}

export async function reviewEdit(field: string, value: string): Promise<DocumentProjection> {
  const r = await fetch("/api/documents/review/edit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ field, value }),
  });
  return r.json();
}

export async function reviewApprove(): Promise<DocumentProjection> {
  const r = await fetch("/api/documents/review/approve", { method: "POST" });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Approve failed");
  return r.json();
}

export async function reviewReject(): Promise<DocumentProjection> {
  const r = await fetch("/api/documents/review/reject", { method: "POST" });
  return r.json();
}

export const previewUrl = (sampleKey: string) =>
  `/api/documents/sample/${sampleKey}/preview`;

// Preview of the exact document the customer uploaded (advisor source view).
export const uploadedPreviewUrl = "/api/documents/uploaded/preview";

export const extractionJsonUrl = "/api/documents/extraction.json";

// Sanitized, reusable structured extraction contract (advisor download/copy).
export async function getExtractionJson(): Promise<Record<string, unknown> | null> {
  const r = await fetch(extractionJsonUrl);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error("Failed to load structured extraction");
  return r.json();
}

// ---- Voice (Screen 2) -------------------------------------------------- //

export type VoiceMessage =
  | { type: "hello"; provider: string; epoch: number }
  | { type: "session"; state: "active" | "idle"; provider: string }
  | { type: "agent_transcript"; text: string; final: boolean }
  | { type: "user_transcript"; text: string; final: boolean }
  | {
      type: "consent";
      status: "requested" | "granted" | "denied" | "consumed" | "expired";
      action: string;
      scope: string | null;
      consent_id: string;
    }
  | { type: "barge_in" }
  | { type: "agent_interrupted" }
  | { type: "audio"; pcm: string }
  | { type: "error"; message: string };

export async function voiceStart(): Promise<void> {
  await fetch("/api/voice/start", { method: "POST" });
}

export async function voiceStop(): Promise<void> {
  await fetch("/api/voice/stop", { method: "POST" });
}

// ---- Case / advisor summary (Screen 3) --------------------------------- //

export type IdentityStatus = "unidentified" | "identifying" | "identified" | "failed";
export type CardStatus = "active" | "blocked" | "replacement_ordered";

export interface CapacityMetrics {
  requested_mortgage: number;
  ltv_pct: number;
  total_debt: number;
  annual_gross_income: number;
  debt_ratio: number;
  total_amort_monthly: number;
  stressed_net_interest_monthly: number;
  living_cost_monthly: number;
  property_running_cost_monthly: number;
  existing_debt_payment_monthly: number;
  total_monthly_costs: number;
  kalp_surplus_monthly: number;
  amortization_tier: string;
  stress_test_rate: number;
  monthly_stressed_payment: number;
  living_cost_estimate: number;
  net_after_stress: number;
  dti_ratio: number;
  dti_flag: "above_soft_guideline" | "within_guideline";
  verdict: "not_affordable_at_stress_rate" | "affordable_with_note" | "affordable";
}

export interface AdvisorSummarySections {
  identity?: { customer?: string; assurance?: string };
  income_provenance?: {
    employer?: string;
    gross_monthly?: number;
    net_monthly?: number;
    provenance?: string;
  };
  requested_loan?: Record<string, unknown>;
  credit_result?: Record<string, unknown>;
  capacity_metrics?: CapacityMetrics;
  customer_preferences?: Record<string, unknown>;
  risks_caveats?: string[];
  meeting?: Record<string, unknown> | null;
}

export interface AdvisorSummary {
  sections: AdvisorSummarySections;
  summary: string;
  flags: string[];
  recommended_action: "advisor_review" | "standard_review";
  final_decision_required: boolean;
  status_text: string;
  decision_text: string;
  updated_at: string;
}

export interface CaseCard {
  card_id: string;
  card_type: string;
  last_four: string;
  status: CardStatus;
}

export interface DemoCaseView {
  case_id: string;
  identity_status: IdentityStatus;
  document_state: DocumentState;
  customer_profile: {
    customer_id: string;
    customer_number: string;
    display_name: string;
    phone_number: string;
    email: string;
    street_address: string;
    postal_code: string;
    city: string;
    country: string;
    preferred_language: string;
    customer_since: string;
    contact_details_updated_at: string | null;
    contact_details_updated_by: string | null;
    existing_products?: string[];
    // Additive fields used by the decision timeline's Employment node.
    employer_name?: string;
    relationship_summary?: string;
  } & Record<string, unknown>;
  credit_result: {
    score: number;
    max_score: number;
    risk_band: string;
    existing_debt_balance: number;
    existing_debt_payment: number;
    defaults: string;
    source: string;
  } | null;
  capacity_result: { metrics: CapacityMetrics } | null;
  booked_meeting:
    | { slot: { slot_id: string; start: string; advisor: string }; booking_reference: string; purpose: string }
    | null;
  cards: CaseCard[];
  replacement_order: { order_reference: string; delivery_estimate: string; reason: string } | null;
  advisor_summary: AdvisorSummary | null;
  outcome: string;
}

export async function getCase(): Promise<DemoCaseView> {
  const r = await fetch("/api/case");
  return r.json();
}

export interface CreditReportResponse {
  status: "complete";
  consent_status: "consumed";
  credit_report: Record<string, unknown>;
}

export async function approveAndFetchCreditReport(): Promise<CreditReportResponse> {
  const r = await fetch("/api/mortgage/credit-report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved: true }),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? "Unable to retrieve the credit report.");
  }
  return r.json();
}
