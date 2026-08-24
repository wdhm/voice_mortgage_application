import { useEffect, useState } from "react";
import {
  getCase,
  getDocumentState,
  type CapacityMetrics,
  type DemoCaseView,
  type DocumentProjection,
  type TimelineEvent,
} from "../lib/api";
import { DocumentPanel } from "./DocumentPanel";
import { SummaryPanel } from "./SummaryPanel";

/**
 * Bank-side live decision timeline — the spine of the advisor view.
 *
 * Six requirement categories a mortgage application must satisfy. Each flips
 * RED (missing) -> AMBER (in progress) -> GREEN (fulfilled) as the Voice Live
 * agent executes tools live. State is purely derived from the sanitized event
 * stream plus case/document state — no backend changes. Each node is an
 * expandable region revealing its backing sub-data; the Income node hosts the
 * advisor income evidence + structured JSON, and the final decision node hosts
 * the advisor summary. A reset (epoch bump) clears events and the case, so every
 * node returns to RED automatically.
 *
 * The final lending decision remains advisor-required (human-in-the-loop).
 */

export type NodeStatus = "missing" | "progress" | "fulfilled";

const ACCEPTED_DOC_STATES = new Set<DocumentProjection["document_state"]>([
  "accepted_automatically",
  "accepted_after_review",
]);

const STATUS_META: Record<NodeStatus, { text: string; icon: string }> = {
  missing: { text: "Missing", icon: "○" },
  progress: { text: "In progress", icon: "◐" },
  fulfilled: { text: "Fulfilled", icon: "✓" },
};

const kr = (n: number | undefined | null) =>
  n === undefined || n === null ? "—" : `${n.toLocaleString("sv-SE")} kr`;

interface NodeView {
  key: string;
  label: string;
  subtitle: string;
  status: NodeStatus;
  body: React.ReactNode;
}

function DataRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="dt-data-row">
      <span className="dt-data-k">{k}</span>
      <span className="dt-data-v">{v}</span>
    </div>
  );
}

function Pending({ text }: { text: string }) {
  return <p className="dt-pending">{text}</p>;
}

function deriveNodes(
  events: TimelineEvent[],
  doc: DocumentProjection | null,
  caseView: DemoCaseView | null,
  refreshKey: number,
  embedded: boolean,
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

  const fields = doc?.fields ?? null;
  const credit = caseView?.credit_result ?? null;
  const metrics: CapacityMetrics | undefined = caseView?.capacity_result?.metrics;
  const profile = caseView?.customer_profile;

  return [
    {
      key: "income",
      label: "Income",
      subtitle: "Verified from the payslip",
      status: incomeStatus,
      // When standalone, host the full advisor income evidence + JSON. When
      // embedded in the bank workspace (which already shows the DocumentPanel in
      // its Income step) render a compact income summary to avoid duplication.
      body: embedded ? (
        incomeAccepted && fields ? (
          <div className="dt-data">
            <DataRow k="Gross (monthly)" v={fields.gross_salary_monthly?.value ?? "—"} />
            <DataRow k="Net (monthly)" v={fields.net_salary_monthly?.value ?? "—"} />
            <DataRow k="Employer" v={fields.employer_name?.value ?? "—"} />
            <DataRow k="Provenance" v={fields.gross_salary_monthly?.provenance ?? "—"} />
          </div>
        ) : (
          <Pending text="Populates when the payslip is accepted." />
        )
      ) : (
        <DocumentPanel role="advisor" refreshKey={refreshKey} />
      ),
    },
    {
      key: "employment",
      label: "Employment",
      subtitle: "Confirmed against the customer profile",
      status: status(crmDone, "Get crm profile", "Get CRM profile"),
      body: crmDone ? (
        <div className="dt-data">
          <DataRow k="Employment type" v={fields?.employment_type?.value ?? "—"} />
          <DataRow k="Employer" v={fields?.employer_name?.value ?? profile?.employer_name ?? "—"} />
          <DataRow k="Relationship" v={profile?.relationship_summary ?? "—"} />
        </div>
      ) : (
        <Pending text="Populates when the agent fetches the CRM profile." />
      ),
    },
    {
      key: "debts",
      label: "Debts & credit",
      subtitle: "Existing commitments assessed",
      status: status(creditDone, "Run credit check", "Run credit check"),
      body: creditDone && credit ? (
        <div className="dt-data">
          <DataRow k="Existing debt balance" v={kr(credit.existing_debt_balance as number)} />
          <DataRow k="Monthly payment" v={kr(credit.existing_debt_payment as number)} />
        </div>
      ) : (
        <Pending text="Populates when the credit check completes." />
      ),
    },
    {
      key: "housing",
      label: "Housing costs",
      subtitle: "Property running and living costs",
      status: status(capacityDone, "Calculate borrowing capacity", "Calculate borrowing capacity"),
      body: capacityDone && metrics ? (
        <div className="dt-data">
          <DataRow k="Property running cost (monthly)" v={kr(metrics.property_running_cost_monthly)} />
          <DataRow k="Living cost (monthly)" v={kr(metrics.living_cost_monthly)} />
        </div>
      ) : (
        <Pending text="Populates when borrowing capacity is calculated." />
      ),
    },
    {
      key: "credit",
      label: "Credit check",
      subtitle: "Credit bureau result",
      status: status(creditDone, "Run credit check", "Run credit check"),
      body: creditDone && credit ? (
        <div className="dt-data">
          <DataRow
            k="Score"
            v={credit.score != null ? `${credit.score} / ${credit.max_score ?? 999}` : "—"}
          />
          <DataRow k="Risk band" v={(credit.risk_band as string) ?? "—"} />
          <DataRow k="Defaults" v={(credit.defaults as string) ?? "—"} />
        </div>
      ) : (
        <Pending text="Populates when the credit check completes." />
      ),
    },
    {
      key: "kalp",
      label: "KALP",
      subtitle: "Kvar-att-leva-på-kalkyl · Left-to-live-on",
      status: status(capacityDone, "Calculate borrowing capacity", "Calculate borrowing capacity"),
      body: capacityDone && metrics ? (
        <div className="dt-data">
          <DataRow k="Monthly surplus (KALP)" v={kr(metrics.kalp_surplus_monthly)} />
          <DataRow k="Total monthly costs" v={kr(metrics.total_monthly_costs)} />
          <DataRow k="Debt ratio" v={metrics.debt_ratio != null ? `${metrics.debt_ratio}×` : "—"} />
          <DataRow k="Loan-to-value" v={metrics.ltv_pct != null ? `${metrics.ltv_pct}%` : "—"} />
        </div>
      ) : (
        <Pending text="Populates when borrowing capacity is calculated." />
      ),
    },
  ];
}

function TimelineNode({ node }: { node: NodeView }) {
  const meta = STATUS_META[node.status];
  return (
    <li className={`dt-node ${node.status}`}>
      <span className="dt-rail" aria-hidden>
        <span className="dt-marker">{meta.icon}</span>
      </span>
      <div className="dt-body">
        <details className="dt-details">
          <summary className="dt-summary">
            <span className="dt-summary-main">
              <span className="dt-node-head">
                <span className="dt-label">{node.label}</span>
                <span className={`dt-status ${node.status}`}>
                  {meta.icon} {meta.text}
                </span>
              </span>
              <span className="dt-node-sub">{node.subtitle}</span>
            </span>
            <span className="dt-chevron" aria-hidden>⌄</span>
          </summary>
          <div className="dt-expand">{node.body}</div>
        </details>
      </div>
    </li>
  );
}

export function DecisionTimeline({
  events,
  embedded = false,
}: {
  events: TimelineEvent[];
  embedded?: boolean;
}) {
  const [doc, setDoc] = useState<DocumentProjection | null>(null);
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);

  const refreshKey = events.length;
  useEffect(() => {
    getDocumentState().then(setDoc).catch(() => setDoc(null));
    getCase().then(setCaseView).catch(() => setCaseView(null));
  }, [refreshKey]);

  const nodes = deriveNodes(events, doc, caseView, refreshKey, embedded);
  const fulfilledCount = nodes.filter((n) => n.status === "fulfilled").length;
  const allFulfilled = fulfilledCount === nodes.length;
  const summary = caseView?.advisor_summary ?? null;

  return (
    <div className={`decision-timeline${embedded ? " embedded" : ""}`}>
      <div className="dt-head">
        <div>
          <p className="pane-title">Decision timeline</p>
          <p className="dt-sub">
            The agent gathers each requirement live. Nodes turn from missing to fulfilled as tools run.
            Expand any node for its evidence.
          </p>
        </div>
        <span className="dt-progress" aria-live="polite">
          {fulfilledCount} / {nodes.length} fulfilled
        </span>
      </div>

      <ol className="dt-list">
        {nodes.map((n) => (
          <TimelineNode key={n.key} node={n} />
        ))}
      </ol>

      <details className={`dt-decision-node ${allFulfilled ? "ready" : "pending"}`}>
        <summary className="dt-decision">
          <span className="dt-decision-icon" aria-hidden>{allFulfilled ? "✓" : "○"}</span>
          <span className="dt-decision-text">
            <strong>
              {allFulfilled ? "Preliminary assessment ready" : "Preliminary assessment pending"}
            </strong>
            <span>Final decision: advisor required</span>
          </span>
          <span className="dt-chevron" aria-hidden>⌄</span>
        </summary>
        <div className="dt-expand">
          {embedded ? (
            summary ? (
              <div className="dt-data">
                <DataRow k="Assessment" v={summary.status_text} />
                <DataRow k="Decision" v={summary.decision_text} />
                <p className="dt-decision-hint">
                  Full advisor summary is in the Advisor review step below.
                </p>
              </div>
            ) : (
              <Pending text="Populates when the advisor summary is written." />
            )
          ) : (
            <SummaryPanel refreshKey={refreshKey} />
          )}
        </div>
      </details>
    </div>
  );
}
