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
  uploaded_document: { filename: string; sample_key: string | null } | null;
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
