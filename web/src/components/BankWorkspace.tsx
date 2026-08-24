import { useEffect, useMemo, useState } from "react";
import {
  getBankPayslipExtractions,
  getCase,
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

  useEffect(() => {
    Promise.all([getCase(), getBankPayslipExtractions()])
      .then(([nextCase, output]) => {
        setCaseView(nextCase);
        setRecords(output.payslips);
        setLoadError(null);
      })
      .catch(() => setLoadError("Payslip extraction data could not be loaded."));
  }, [refreshKey]);

  const emmaAccepted = caseView ? ACCEPTED_STATES.includes(caseView.document_state) : false;
  const queue = useMemo(() => records, [records]);

  const flaggedCount = emmaAccepted ? 0 : 1;
  const selectedApplicant = queue.find((record) => record.id === selected) ?? queue.find((record) => record.id === "emma");

  return (
    <main className="bank-shell">
      <aside className="bank-case-menu">
        <div className="bank-user">
          <span className="bank-user-avatar" aria-hidden>BB</span>
          <div>
            <strong>Payslip review desk</strong>
            <span>Bengt Bäckström · Bank representative</span>
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

        <ul className="payslip-queue" aria-label="Payslip review queue">
          {queue.map((record) => {
            const accepted = record.status === "accepted";
            return (
              <li key={record.id}>
                <button
                  type="button"
                  className={`queue-row ${record.id === selected ? "active" : ""} ${accepted ? "ok" : "flagged"}`}
                  aria-pressed={record.id === selected}
                  onClick={() => setSelected(record.id)}
                >
                  <span className="customer-initials" aria-hidden>{record.customer.initials}</span>
                  <span className="queue-row-body">
                    <strong>{record.customer.name}</strong>
                    <small>{record.fields.employer_name ?? "Employer unavailable"}</small>
                  </span>
                  <span className={`payslip-chip ${accepted ? "ok" : "flagged"}`}>
                    <span aria-hidden>{accepted ? "●" : "▲"}</span>
                    {accepted ? "Accepted" : "Rejected"}
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
          <EmmaCaseDetail caseView={caseView} accepted={emmaAccepted} record={selectedApplicant} />
        ) : selectedApplicant ? (
          <AcceptedCaseDetail record={selectedApplicant} />
        ) : (
          <p>Loading payslip queue…</p>
        )}
      </section>
    </main>
  );
}

function EmmaCaseDetail({
  caseView,
  accepted,
  record,
}: {
  caseView: DemoCaseView | null;
  accepted: boolean;
  record: BankPayslipRecord;
}) {
  const reason = caseView?.rejection_reason;
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
        <span className={`payslip-chip large ${accepted ? "ok" : "flagged"}`}>
          <span aria-hidden>{accepted ? "●" : "▲"}</span>
          {accepted ? "Payslip accepted" : "Payslip rejected"}
        </span>
      </header>

      {accepted ? (
        <section className="payslip-banner ok" role="status">
          <div>
            <h2>Payslip accepted — income verified</h2>
            <p>A clear payslip was received and read automatically. The mortgage application has the income evidence it needs.</p>
          </div>
        </section>
      ) : (
        <section className="payslip-banner flagged" role="status">
          <div>
            <h2>Payslip rejected — unreadable scan</h2>
            <p>{reason ?? "The document could not be read — the scan is too blurred to extract the income fields. A notification has been sent to the customer asking them to re-upload a clear copy."}</p>
          </div>
        </section>
      )}

      <PayslipEvidence record={record} flagged={!accepted} />
      {!accepted && (
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
  flagged = false,
}: {
  record: BankPayslipRecord;
  flagged?: boolean;
}) {
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
          <div className={`payslip-frame ${flagged ? "flagged" : ""}`}>
            <iframe
              key={`${record.id}-${record.status}`}
              title={`Submitted payslip for ${record.customer.name}`}
              src={`/api/documents/bank-extractions/${record.id}/preview`}
            />
          </div>
        </div>
        <aside className={`extracted-data-panel ${flagged ? "flagged" : ""}`}>
          <div className="extracted-data-head">
            <div>
              <p className="pane-title">Mandatory extracted data</p>
              <h3>{flagged ? "No readable values" : "Income fields collected"}</h3>
            </div>
            <span className={`payslip-chip ${flagged ? "flagged" : "ok"}`}>
              {flagged ? "Rejected" : "Complete"}
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
