import { useEffect, useState } from "react";
import {
  getCase,
  getDocumentState,
  type DemoCaseView,
  type DocumentProjection,
  type TimelineEvent,
} from "../lib/api";

/**
 * Bank-side live decision timeline — the spine of the advisor view.
 *
 * Six requirement categories a mortgage application must satisfy. Each flips
 * RED (missing) -> AMBER (in progress) -> GREEN (fulfilled) as the Voice Live
 * agent executes tools live. State is purely derived from the sanitized event
 * stream plus case/document state — no backend changes. A reset (epoch bump)
 * clears events and the case, so every node returns to RED automatically.
 *
 * The final lending decision remains advisor-required (human-in-the-loop).
 */

export type NodeStatus = "missing" | "progress" | "fulfilled";

const ACCEPTED_DOC_STATES = new Set<DocumentProjection["document_state"]>([
  "accepted_automatically",
  "accepted_after_review",
]);

interface NodeView {
  key: string;
  label: string;
  subtitle: string;
  status: NodeStatus;
}

const STATUS_META: Record<NodeStatus, { text: string; icon: string }> = {
  missing: { text: "Missing", icon: "○" },
  progress: { text: "In progress", icon: "◐" },
  fulfilled: { text: "Fulfilled", icon: "✓" },
};

function deriveNodes(
  events: TimelineEvent[],
  doc: DocumentProjection | null,
): NodeView[] {
  const completed = (label: string) =>
    events.some((e) => e.event_type === "tool.completed" && e.display.label === label);
  // The dispatcher emits tool.requested with the "pretty" capitalized tool name,
  // which differs from the completed ToolOutcome.label — match it separately.
  const inFlight = (pretty: string, completedLabel: string) =>
    !completed(completedLabel) &&
    events.some((e) => e.event_type === "tool.requested" && e.display.label === pretty);

  const status = (
    fulfilled: boolean,
    pretty: string,
    completedLabel: string,
  ): NodeStatus => (fulfilled ? "fulfilled" : inFlight(pretty, completedLabel) ? "progress" : "missing");

  const docState = doc?.document_state ?? "empty";
  const incomeAccepted = ACCEPTED_DOC_STATES.has(docState);
  const incomeStatus: NodeStatus = incomeAccepted
    ? "fulfilled"
    : docState === "analyzing" || docState === "review_required"
      ? "progress"
      : "missing";

  const crmDone = completed("Get CRM profile");
  const creditDone = completed("Run credit check");
  const capacityDone = completed("Calculate borrowing capacity");

  return [
    {
      key: "income",
      label: "Income",
      subtitle: "Verified from the payslip",
      status: incomeStatus,
    },
    {
      key: "employment",
      label: "Employment",
      subtitle: "Confirmed against the customer profile",
      status: status(crmDone, "Get crm profile", "Get CRM profile"),
    },
    {
      key: "debts",
      label: "Debts & credit",
      subtitle: "Existing commitments assessed",
      status: status(creditDone, "Run credit check", "Run credit check"),
    },
    {
      key: "housing",
      label: "Housing costs",
      subtitle: "Property running and living costs",
      status: status(capacityDone, "Calculate borrowing capacity", "Calculate borrowing capacity"),
    },
    {
      key: "credit",
      label: "Credit check",
      subtitle: "Credit bureau result",
      status: status(creditDone, "Run credit check", "Run credit check"),
    },
    {
      key: "kalp",
      label: "KALP",
      subtitle: "Kvar-att-leva-på-kalkyl · Left-to-live-on",
      status: status(capacityDone, "Calculate borrowing capacity", "Calculate borrowing capacity"),
    },
  ];
}

export function DecisionTimeline({ events }: { events: TimelineEvent[] }) {
  const [doc, setDoc] = useState<DocumentProjection | null>(null);
  // Kept for M2 (sub-data). Case/doc are re-fetched whenever the timeline advances.
  const [, setCaseView] = useState<DemoCaseView | null>(null);

  const refreshKey = events.length;
  useEffect(() => {
    getDocumentState().then(setDoc).catch(() => setDoc(null));
    getCase().then(setCaseView).catch(() => setCaseView(null));
  }, [refreshKey]);

  const nodes = deriveNodes(events, doc);
  const fulfilledCount = nodes.filter((n) => n.status === "fulfilled").length;
  const allFulfilled = fulfilledCount === nodes.length;

  return (
    <div className="decision-timeline">
      <div className="dt-head">
        <div>
          <p className="pane-title">Decision timeline</p>
          <p className="dt-sub">
            The agent gathers each requirement live. Nodes turn from missing to fulfilled as tools run.
          </p>
        </div>
        <span className="dt-progress" aria-live="polite">
          {fulfilledCount} / {nodes.length} fulfilled
        </span>
      </div>

      <ol className="dt-list">
        {nodes.map((n) => (
          <li key={n.key} className={`dt-node ${n.status}`}>
            <span className="dt-rail" aria-hidden>
              <span className="dt-marker">{STATUS_META[n.status].icon}</span>
            </span>
            <div className="dt-body">
              <div className="dt-node-head">
                <span className="dt-label">{n.label}</span>
                <span className={`dt-status ${n.status}`}>
                  {STATUS_META[n.status].icon} {STATUS_META[n.status].text}
                </span>
              </div>
              <span className="dt-node-sub">{n.subtitle}</span>
            </div>
          </li>
        ))}
      </ol>

      <div className={`dt-decision ${allFulfilled ? "ready" : "pending"}`}>
        <span className="dt-decision-icon" aria-hidden>{allFulfilled ? "✓" : "○"}</span>
        <div>
          <strong>
            {allFulfilled
              ? "Preliminary assessment ready"
              : "Preliminary assessment pending"}
          </strong>
          <span>Final decision: advisor required</span>
        </div>
      </div>
    </div>
  );
}
