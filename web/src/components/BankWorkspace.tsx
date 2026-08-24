import { useEffect, useMemo, useState } from "react";
import { getCase, type DemoCaseView, type DocumentState } from "../lib/api";

// Green document states = the payslip is verified. Anything else on Emma's live case
// means the bank still needs a clean payslip (red / attention).
const ACCEPTED_STATES: DocumentState[] = ["accepted_automatically", "accepted_after_review"];

type QueueApplicant = {
  id: string;
  name: string;
  initials: string;
  product: string;
  // Decorative applicants are always accepted (bulk context); "emma" is driven by live case state.
  kind: "green" | "emma";
};

// Bengt's bulk payslip-review queue. The decorative applicants set the "reviewing in bulk"
// context; Emma is the real case whose status comes from the live demo state.
const DECOR: QueueApplicant[] = [
  { id: "johan", name: "Johan Bergström", initials: "JB", product: "Mortgage application", kind: "green" },
  { id: "sara", name: "Sara Nyström", initials: "SN", product: "Mortgage application", kind: "green" },
  { id: "anders", name: "Anders Karlsson", initials: "AK", product: "Mortgage application", kind: "green" },
  { id: "linnea", name: "Linnéa Holm", initials: "LH", product: "Mortgage application", kind: "green" },
];

export function BankWorkspace({ refreshKey }: { refreshKey: number }) {
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);
  const [selected, setSelected] = useState<string>("emma");

  useEffect(() => {
    getCase().then(setCaseView).catch(() => {});
  }, [refreshKey]);

  const emmaAccepted = caseView ? ACCEPTED_STATES.includes(caseView.document_state) : false;
  const emmaName = caseView?.customer_profile.display_name ?? "Emma Lindberg";

  const queue: QueueApplicant[] = useMemo(
    () => [
      DECOR[0],
      DECOR[1],
      { id: "emma", name: emmaName, initials: "EL", product: "Mortgage application", kind: "emma" },
      DECOR[2],
      DECOR[3],
    ],
    [emmaName],
  );

  const flaggedCount = emmaAccepted ? 0 : 1;
  const selectedApplicant = queue.find((a) => a.id === selected) ?? queue[2];

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
          <b>{queue.length}</b>
        </div>
        {flaggedCount > 0 && (
          <p className="queue-flag-summary" role="status">
            {flaggedCount} payslip needs attention
          </p>
        )}

        <ul className="payslip-queue" aria-label="Payslip review queue">
          {queue.map((a) => {
            const accepted = a.kind === "green" ? true : emmaAccepted;
            const isEmma = a.kind === "emma";
            return (
              <li key={a.id}>
                <button
                  type="button"
                  className={`queue-row ${a.id === selected ? "active" : ""} ${accepted ? "ok" : "flagged"}`}
                  aria-pressed={a.id === selected}
                  onClick={() => setSelected(a.id)}
                >
                  <span className="customer-initials" aria-hidden>{a.initials}</span>
                  <span className="queue-row-body">
                    <strong>{a.name}</strong>
                    <small>{a.product}</small>
                  </span>
                  <span className={`payslip-chip ${accepted ? "ok" : "flagged"}`}>
                    <span aria-hidden>{accepted ? "●" : "▲"}</span>
                    {accepted ? "Accepted" : isEmma ? "Rejected" : "Accepted"}
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
        {selectedApplicant.kind === "emma" ? (
          <EmmaCaseDetail caseView={caseView} accepted={emmaAccepted} name={emmaName} />
        ) : (
          <DecorativeCaseDetail name={selectedApplicant.name} />
        )}
      </section>
    </main>
  );
}

function EmmaCaseDetail({
  caseView,
  accepted,
  name,
}: {
  caseView: DemoCaseView | null;
  accepted: boolean;
  name: string;
}) {
  const reason = caseView?.rejection_reason;
  return (
    <>
      <header className="bank-case-header">
        <div>
          <p className="eyebrow">Mortgage payslip · {caseView?.case_id ?? "case-emma"}</p>
          <h1>{name}</h1>
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
            <p>{reason ?? "The payslip could not be read. Ask the customer to re-upload a clear copy."}</p>
          </div>
        </section>
      )}

      <section className="payslip-preview-card">
        <div className="bank-card-title">
          <div>
            <p className="pane-title">Submitted payslip</p>
            <h3>
              {accepted
                ? "lonespec-northstar-hifi.pdf"
                : caseView?.uploaded_document?.filename ?? "lonespec-northstar-scan.html"}
            </h3>
          </div>
          <span className="evidence-source">Content Understanding · simulated</span>
        </div>
        <div className={`payslip-frame ${accepted ? "" : "flagged"}`}>
          <iframe
            key={accepted ? "hifi" : "scan"}
            title="Submitted payslip preview"
            src={
              accepted
                ? "/api/documents/sample/high_confidence/preview"
                : "/api/documents/sample/low_confidence/preview"
            }
          />
        </div>
        {!accepted && (
          <p className="evidence-source">
            The customer can re-upload a clear payslip from their own view; this case flips to green
            automatically once a readable copy is accepted.
          </p>
        )}
      </section>
    </>
  );
}

function DecorativeCaseDetail({ name }: { name: string }) {
  return (
    <>
      <header className="bank-case-header">
        <div>
          <p className="eyebrow">Mortgage payslip</p>
          <h1>{name}</h1>
          <p>Payslip read automatically — no action needed.</p>
        </div>
        <span className="payslip-chip large ok">
          <span aria-hidden>●</span>
          Payslip accepted
        </span>
      </header>
      <section className="payslip-banner ok" role="status">
        <div>
          <h2>Payslip accepted — income verified</h2>
          <p>This payslip passed automated review. It stays in the queue for context while Bengt works the flagged case.</p>
        </div>
      </section>
    </>
  );
}
