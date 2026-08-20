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
