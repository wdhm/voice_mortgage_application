import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getBankPayslipExtractions,
  getCase,
  reviewApprove,
  type BankPayslipRecord,
  type DemoCaseView,
  type DocumentState,
  type FieldName,
} from "../lib/api";

// Green document states = the payslip is verified. Anything else on Emma's live case
// means the bank still needs a clean payslip (red / attention).
const ACCEPTED_STATES: DocumentState[] = ["accepted_automatically", "accepted_after_review"];

const FIELD_LABELS: Record<FieldName, string> = {
  employer_name: "Employer name",
  gross_salary_monthly: "Gross monthly salary",
  net_salary_monthly: "Net monthly salary",
  employment_type: "Employment type",
  pay_date: "Pay date",
};

const FIELD_NAMES = Object.keys(FIELD_LABELS) as FieldName[];

function formatField(name: FieldName, value: string | number | null): string {
  if (value === null) return "Not extracted";
  if (name === "gross_salary_monthly" || name === "net_salary_monthly") {
    return `${new Intl.NumberFormat("sv-SE").format(Number(value))} SEK`;
  }
  return String(value);
}

export function BankWorkspace({ refreshKey }: { refreshKey: number }) {
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);
  const [records, setRecords] = useState<BankPayslipRecord[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string>("emma");
  const [workspacePage, setWorkspacePage] = useState<"overview" | "case">("overview");
  const [approving, setApproving] = useState(false);

  const loadWorkspace = useCallback(() => {
    Promise.all([getCase(), getBankPayslipExtractions()])
      .then(([nextCase, output]) => {
        setCaseView(nextCase);
        setRecords(output.payslips);
        setLoadError(null);
      })
      .catch(() => setLoadError("Payslip extraction data could not be loaded."));
  }, []);

  useEffect(() => {
    loadWorkspace();
  }, [refreshKey]);

  const emmaAccepted = caseView ? ACCEPTED_STATES.includes(caseView.document_state) : false;
  const emmaReviewRequired = caseView?.document_state === "review_required";
  const queue = useMemo(() => records, [records]);

  const flaggedCount = emmaAccepted || emmaReviewRequired ? 0 : 1;
  const selectedApplicant = queue.find((record) => record.id === selected) ?? queue.find((record) => record.id === "emma");
  const openApplication = (id: string) => {
    setSelected(id);
    setWorkspacePage("case");
  };

  const approveEmma = async () => {
    setApproving(true);
    setLoadError(null);
    try {
      await reviewApprove();
      loadWorkspace();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "The payslip could not be approved.");
    } finally {
      setApproving(false);
    }
  };

  if (workspacePage === "overview") {
    return (
      <BankApplicationOverview
        caseView={caseView}
        records={queue}
        loadError={loadError}
        onOpen={openApplication}
      />
    );
  }

  return (
    <main className="bank-shell">
      <aside className="bank-case-menu">
        <button
          type="button"
          className="bank-overview-link"
          onClick={() => setWorkspacePage("overview")}
        >
          ← Application overview
        </button>
        <div className="bank-user">
          <span className="bank-user-avatar" aria-hidden>S</span>
          <div>
            <strong>Payslip review desk</strong>
            <span>Simon · Bank representative</span>
          </div>
        </div>

        <div className="case-queue-heading">
          <span>Mortgage payslips</span>
          <b>{queue.length || 5}</b>
        </div>
        {flaggedCount > 0 && (
          <p className="queue-flag-summary" role="status">
            {flaggedCount} payslip needs attention
          </p>
        )}
        {emmaReviewRequired && (
          <p className="queue-review-summary" role="status">
            1 payslip is awaiting manual approval
          </p>
        )}

        <ul className="payslip-queue" aria-label="Payslip review queue">
          {queue.map((record) => {
            const accepted = record.status === "accepted";
            const reviewRequired = record.status === "review_required";
            const tone = accepted ? "ok" : reviewRequired ? "review" : "flagged";
            return (
              <li key={record.id}>
                <button
                  type="button"
                  className={`queue-row ${record.id === selected ? "active" : ""} ${tone}`}
                  aria-pressed={record.id === selected}
                  onClick={() => openApplication(record.id)}
                >
                  <span className="customer-initials" aria-hidden>{record.customer.initials}</span>
                  <span className="queue-row-body">
                    <strong>{record.customer.name}</strong>
                    <small>{record.fields.employer_name ?? "Employer unavailable"}</small>
                  </span>
                  <span className={`payslip-chip ${tone}`}>
                    <span aria-hidden>{accepted ? "●" : reviewRequired ? "●" : "▲"}</span>
                    {accepted ? "Accepted" : reviewRequired ? "Review" : "Rejected"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        <div className="bank-queue-note">
          <strong>Human decision required</strong>
          <span>AI output supports review but never makes the final lending decision.</span>
        </div>
      </aside>

      <section className="bank-case-content">
        {loadError ? (
          <p className="queue-load-error" role="alert">{loadError}</p>
        ) : selectedApplicant?.id === "emma" ? (
          <EmmaCaseDetail
            caseView={caseView}
            accepted={emmaAccepted}
            record={selectedApplicant}
            approving={approving}
            onApprove={() => void approveEmma()}
          />
        ) : selectedApplicant ? (
          <AcceptedCaseDetail record={selectedApplicant} />
        ) : (
          <p>Loading payslip queue…</p>
        )}
      </section>
    </main>
  );
}

function BankApplicationOverview({
  caseView,
  records,
  loadError,
  onOpen,
}: {
  caseView: DemoCaseView | null;
  records: BankPayslipRecord[];
  loadError: string | null;
  onOpen: (id: string) => void;
}) {
  const actionRequired = records.filter((record) => record.status !== "accepted").length;
  const appointmentBooked = caseView?.booked_meeting !== null;

  const applicationStatus = (record: BankPayslipRecord) => {
    if (record.status === "rejected") {
      return {
        stage: "Income verification",
        label: "Customer action needed",
        detail: "Unreadable payslip",
        tone: "attention",
      };
    }
    if (record.status === "review_required") {
      return {
        stage: "Income verification",
        label: "Manual review",
        detail: "Document ready for approval",
        tone: "review",
      };
    }
    if (record.id === "emma" && appointmentBooked) {
      return {
        stage: "Advisor appointment",
        label: "Meeting booked",
        detail: "Ready for advisor review",
        tone: "booked",
      };
    }
    return {
      stage: "Appointment",
      label: "Income verified",
      detail: "Waiting for customer booking",
      tone: "verified",
    };
  };

  return (
    <main className="bank-overview">
      <header className="bank-overview-hero">
        <div>
          <p className="eyebrow">Mortgage operations</p>
          <h1>Good morning, Simon</h1>
          <p>Here is the current status of your ongoing mortgage applications.</p>
        </div>
        <div className="bank-overview-date">
          <span>Portfolio</span>
          <strong>{records.length} active applications</strong>
        </div>
      </header>

      <section className="bank-portfolio-stats" aria-label="Application summary">
        <article>
          <span>Ongoing applications</span>
          <strong>{records.length}</strong>
          <small>Assigned to your review desk</small>
        </article>
        <article className={actionRequired ? "attention" : ""}>
          <span>Needs attention</span>
          <strong>{actionRequired}</strong>
          <small>Customer or manual action required</small>
        </article>
        <article>
          <span>Income verified</span>
          <strong>{records.filter((record) => record.status === "accepted").length}</strong>
          <small>Ready for the appointment stage</small>
        </article>
      </section>

      <section className="bank-applications-card">
        <div className="bank-applications-heading">
          <div>
            <p className="eyebrow">Application portfolio</p>
            <h2>Ongoing applications</h2>
          </div>
          <span>Updated live</span>
        </div>
        {loadError ? (
          <p className="queue-load-error" role="alert">{loadError}</p>
        ) : records.length === 0 ? (
          <p className="bank-overview-empty">Loading applications…</p>
        ) : (
          <div className="bank-applications-table" role="table" aria-label="Ongoing mortgage applications">
            <div className="bank-application-row header" role="row">
              <span role="columnheader">Applicant</span>
              <span role="columnheader">Application</span>
              <span role="columnheader">Current stage</span>
              <span role="columnheader">Status</span>
              <span aria-hidden />
            </div>
            {records.map((record, index) => {
              const status = applicationStatus(record);
              return (
                <button
                  key={record.id}
                  type="button"
                  className="bank-application-row"
                  onClick={() => onOpen(record.id)}
                  role="row"
                >
                  <span className="bank-applicant" role="cell">
                    <span className="customer-initials" aria-hidden>{record.customer.initials}</span>
                    <span>
                      <strong>{record.customer.name}</strong>
                      <small>{record.customer.city}</small>
                    </span>
                  </span>
                  <span className="bank-application-id" role="cell">
                    <strong>{record.id === "emma" ? caseView?.case_id ?? "MOR-104857" : `MOR-${104862 + index}`}</strong>
                    <small>Mortgage application</small>
                  </span>
                  <span className="bank-stage" role="cell">
                    <strong>{status.stage}</strong>
                    <small>{status.detail}</small>
                  </span>
                  <span role="cell">
                    <span className={`application-status ${status.tone}`}>{status.label}</span>
                  </span>
                  <span className="application-open" aria-hidden>→</span>
                </button>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}

function EmmaCaseDetail({
  caseView,
  accepted,
  record,
  approving,
  onApprove,
}: {
  caseView: DemoCaseView | null;
  accepted: boolean;
  record: BankPayslipRecord;
  approving: boolean;
  onApprove: () => void;
}) {
  const reason = caseView?.rejection_reason;
  const reviewRequired = record.status === "review_required";
  const tone = accepted ? "ok" : reviewRequired ? "review" : "flagged";
  return (
    <>
      <header className="bank-case-header">
        <div>
          <p className="eyebrow">Mortgage payslip · {caseView?.case_id ?? "case-emma"}</p>
          <h1>{record.customer.name}</h1>
          <p>
            Customer {caseView?.customer_profile.customer_number ?? "1048 572 963"} ·{" "}
            {caseView?.customer_profile.city ?? "Täby"}
          </p>
        </div>
        <span className={`payslip-chip large ${tone}`}>
          <span aria-hidden>{accepted || reviewRequired ? "●" : "▲"}</span>
          {accepted ? "Payslip accepted" : reviewRequired ? "Awaiting approval" : "Payslip rejected"}
        </span>
      </header>

      {accepted ? (
        <section className="payslip-banner ok" role="status">
          <div>
            <h2>Payslip accepted — income verified</h2>
            <p>A clear payslip was received and read automatically. The mortgage application has the income evidence it needs.</p>
          </div>
        </section>
      ) : reviewRequired ? (
        <section className="payslip-banner review" role="status">
          <div>
            <h2>Automated review passed — manual approval required</h2>
            <p>All mandatory income fields were extracted. Confirm the values before accepting the payslip.</p>
          </div>
          <button type="button" className="icon-btn primary" onClick={onApprove} disabled={approving}>
            {approving ? "Approving…" : "Approve payslip"}
          </button>
        </section>
      ) : (
        <section className="payslip-banner flagged" role="status">
          <div>
            <h2>Payslip rejected — unreadable scan</h2>
            <p>{reason ?? "The document could not be read — the scan is too blurred to extract the income fields. A notification has been sent to the customer asking them to re-upload a clear copy."}</p>
          </div>
        </section>
      )}

      <PayslipEvidence record={record} tone={tone} />
      {!accepted && !reviewRequired && (
        <p className="evidence-source payslip-follow-up">
          The customer can re-upload a clear payslip from their own view; this case flips to green
          automatically once a readable copy is accepted.
        </p>
      )}
    </>
  );
}

function AcceptedCaseDetail({ record }: { record: BankPayslipRecord }) {
  return (
    <>
      <header className="bank-case-header">
        <div>
          <p className="eyebrow">Mortgage payslip</p>
          <h1>{record.customer.name}</h1>
          <p>
            Customer {record.customer.customer_number} · {record.customer.city} ·{" "}
            {record.fields.employer_name}
          </p>
        </div>
        <span className="payslip-chip large ok">
          <span aria-hidden>●</span>
          Payslip accepted
        </span>
      </header>
      <section className="payslip-banner ok" role="status">
        <div>
          <h2>Payslip accepted — income verified</h2>
          <p>This payslip passed automated review. All mandatory income fields were extracted.</p>
        </div>
      </section>
      <PayslipEvidence record={record} />
    </>
  );
}

function PayslipEvidence({
  record,
  tone = "ok",
}: {
  record: BankPayslipRecord;
  tone?: "ok" | "flagged" | "review";
}) {
  const flagged = tone === "flagged";
  const reviewRequired = tone === "review";
  const previewSrc =
    record.id === "emma" && !flagged && record.document.uploaded_at
      ? `/api/documents/uploaded/preview?ts=${encodeURIComponent(record.document.uploaded_at)}`
      : `/api/documents/bank-extractions/${record.id}/preview`;
  return (
    <section className="payslip-preview-card">
      <div className="payslip-review-grid">
        <div className="payslip-document-pane">
          <div className="bank-card-title">
            <div>
              <p className="pane-title">Submitted payslip</p>
              <h3>{record.document.filename}</h3>
            </div>
            <span className="evidence-source">Content Understanding · simulated</span>
          </div>
          <div className={`payslip-frame ${tone}`}>
            <iframe
              key={`${record.id}-${record.status}`}
              title={`Submitted payslip for ${record.customer.name}`}
              src={previewSrc}
            />
          </div>
        </div>
        <aside className={`extracted-data-panel ${tone}`}>
          <div className="extracted-data-head">
            <div>
              <p className="pane-title">Mandatory extracted data</p>
              <h3>
                {flagged ? "No readable values" : reviewRequired ? "Ready for manual approval" : "Income fields collected"}
              </h3>
            </div>
            <span className={`payslip-chip ${tone}`}>
              {flagged ? "Rejected" : reviewRequired ? "Review" : "Complete"}
            </span>
          </div>
          <dl className="extracted-field-list">
            {FIELD_NAMES.map((name) => {
              const value = record.fields[name];
              const confidence = record.confidence[name];
              return (
                <div key={name} className={value === null ? "missing" : ""}>
                  <dt>{FIELD_LABELS[name]}</dt>
                  <dd>{formatField(name, value)}</dd>
                  <span>{confidence === null ? "Unavailable" : `${Math.round(confidence * 100)}% confidence`}</span>
                </div>
              );
            })}
          </dl>
          <p className="json-source">
            Developer JSON: <code>app/documents/extracted_payslips.json</code>
          </p>
        </aside>
      </div>
    </section>
  );
}
