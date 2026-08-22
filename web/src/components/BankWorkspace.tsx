import { useEffect, useState } from "react";
import { getCase, type DemoCaseView } from "../lib/api";
import { DocumentPanel } from "./DocumentPanel";
import { MortgageProgress } from "./MortgageChecklist";
import { SummaryPanel } from "./SummaryPanel";

const kr = (value: number | undefined) =>
  value === undefined ? "—" : `${value.toLocaleString("sv-SE")} kr`;

export function BankWorkspace({
  refreshKey,
  incomeVerified,
  affordabilityComplete,
  bankReviewComplete,
  appointmentComplete,
}: {
  refreshKey: number;
  incomeVerified: boolean;
  affordabilityComplete: boolean;
  bankReviewComplete: boolean;
  appointmentComplete: boolean;
}) {
  const [activeStep, setActiveStep] = useState(1);
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);

  useEffect(() => {
    getCase().then(setCaseView).catch(() => {});
  }, [refreshKey]);

  useEffect(() => {
    if (appointmentComplete) setActiveStep(4);
    else if (bankReviewComplete) setActiveStep(3);
    else if (affordabilityComplete) setActiveStep(2);
    else setActiveStep(1);
  }, [incomeVerified, affordabilityComplete, bankReviewComplete, appointmentComplete]);

  const status = appointmentComplete
    ? "Advisor appointment booked"
    : bankReviewComplete
      ? "Ready for advisor decision"
    : affordabilityComplete
      ? "Affordability assessed"
      : incomeVerified
        ? "Credit assessment pending"
        : "Income evidence pending";

  return (
    <main className="bank-shell">
      <aside className="bank-case-menu">
        <div className="bank-user">
          <span className="bank-user-avatar" aria-hidden>BA</span>
          <div>
            <strong>Mortgage desk</strong>
            <span>Bank representative</span>
          </div>
        </div>
        <div className="case-queue-heading">
          <span>Active cases</span>
          <b>1</b>
        </div>
        <button type="button" className="case-queue-item active">
          <span className="customer-initials" aria-hidden>EL</span>
          <span>
            <strong>{caseView?.customer_profile.display_name ?? "Emma Lindberg"}</strong>
            <small>Mortgage application</small>
            <em>{status}</em>
          </span>
        </button>
        <div className="bank-queue-note">
          <strong>Human decision required</strong>
          <span>AI output supports review but never makes the final lending decision.</span>
        </div>
      </aside>

      <section className="bank-case-content">
        <header className="bank-case-header">
          <div>
            <p className="eyebrow">Mortgage case · {caseView?.case_id ?? "case-emma"}</p>
            <h1>{caseView?.customer_profile.display_name ?? "Emma Lindberg"}</h1>
            <p>
              Customer {caseView?.customer_profile.customer_number ?? "1048 572 963"} ·{" "}
              {caseView?.customer_profile.city ?? "Täby"}
            </p>
          </div>
          <span className={`case-status ${bankReviewComplete ? "review" : ""}`}>{status}</span>
        </header>

        <MortgageProgress
          activeStep={activeStep}
          incomeVerified={incomeVerified}
          affordabilityComplete={affordabilityComplete}
          bankReviewComplete={bankReviewComplete}
          appointmentComplete={appointmentComplete}
          onOpenStep={setActiveStep}
        />

        <div className="bank-stage-heading">
          <div>
            <p className="eyebrow">Representative workspace</p>
            <h2>
              {activeStep === 1
                ? "Income evidence review"
                : activeStep === 2
                  ? "Credit & affordability evidence"
                  : activeStep === 3
                    ? "Advisor review"
                    : "Customer appointment"}
            </h2>
          </div>
          <span>Live customer case</span>
        </div>

        {activeStep === 1 && <DocumentPanel role="advisor" refreshKey={refreshKey} />}
        {activeStep === 2 && <BankAffordability caseView={caseView} />}
        {activeStep === 3 && <SummaryPanel refreshKey={refreshKey} />}
        {activeStep === 4 && <BankAppointment caseView={caseView} />}
      </section>
    </main>
  );
}

function BankAppointment({ caseView }: { caseView: DemoCaseView | null }) {
  const meeting = caseView?.booked_meeting;
  if (!meeting) {
    return (
      <div className="bank-empty-state">
        <span aria-hidden>○</span>
        <div>
          <h3>No appointment booked</h3>
          <p>The customer can arrange an advisor meeting in the final application step.</p>
        </div>
      </div>
    );
  }
  return (
    <section className="bank-evidence-card bank-appointment-card">
      <div className="bank-card-title">
        <div>
          <p className="pane-title">Confirmed appointment</p>
          <h3>{new Date(meeting.slot.start).toLocaleString("en-GB")}</h3>
        </div>
        <span className="assessment-chip ok">Booked</span>
      </div>
      <dl className="bank-evidence-list">
        <div><dt>Advisor</dt><dd>{meeting.slot.advisor}</dd></div>
        <div><dt>Purpose</dt><dd>{meeting.purpose}</dd></div>
        <div><dt>Booking reference</dt><dd>{meeting.booking_reference}</dd></div>
      </dl>
    </section>
  );
}

function BankAffordability({ caseView }: { caseView: DemoCaseView | null }) {
  const credit = caseView?.credit_result;
  const metrics = caseView?.capacity_result?.metrics;
  const flagged = metrics?.dti_flag === "above_soft_guideline";

  if (!credit) {
    return (
      <div className="bank-empty-state">
        <span aria-hidden>○</span>
        <div>
          <h3>Waiting for customer consent</h3>
          <p>The credit check appears here only after the customer gives explicit verbal consent.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bank-evidence-grid">
      <section className="bank-evidence-card">
        <div className="bank-card-title">
          <div>
            <p className="pane-title">Credit check</p>
            <h3>{credit.score} / {credit.max_score}</h3>
          </div>
          <span className="assessment-chip ok">{credit.risk_band} risk</span>
        </div>
        <dl className="bank-evidence-list">
          <div><dt>Payment remarks</dt><dd>{credit.defaults === "none" ? "None" : credit.defaults}</dd></div>
          <div><dt>Existing commitment</dt><dd>Car loan</dd></div>
          <div><dt>Outstanding balance</dt><dd>{kr(credit.existing_debt_balance)}</dd></div>
          <div><dt>Monthly payment</dt><dd>{kr(credit.existing_debt_payment)}</dd></div>
        </dl>
        <p className="evidence-source">Mock credit bureau · consent-gated server-side</p>
      </section>

      {metrics ? (
        <section className={`bank-evidence-card ${flagged ? "warning" : ""}`}>
          <div className="bank-card-title">
            <div>
              <p className="pane-title">Affordability assessment</p>
              <h3>{metrics.verdict.replace(/_/g, " ")}</h3>
            </div>
            <span className={`assessment-chip ${flagged ? "warning" : "ok"}`}>
              {flagged ? "Advisor note" : "Within guideline"}
            </span>
          </div>
          <dl className="bank-evidence-list">
            <div><dt>Requested mortgage</dt><dd>{kr(metrics.requested_mortgage)}</dd></div>
            <div><dt>Loan-to-value</dt><dd>{metrics.ltv_pct}%</dd></div>
            <div><dt>Amortization tier</dt><dd>{metrics.amortization_tier}</dd></div>
            <div><dt>Stress-test rate</dt><dd>{Math.round(metrics.stress_test_rate * 100)}%</dd></div>
            <div><dt>Net after stress</dt><dd>{kr(metrics.net_after_stress)} / month</dd></div>
            <div className={flagged ? "warning-row" : ""}>
              <dt>Debt-to-income</dt>
              <dd>{metrics.dti_ratio}x {flagged ? "· above 4.5x guideline" : "· within guideline"}</dd>
            </div>
          </dl>
          <p className="evidence-source">Deterministic calculation · preliminary only</p>
        </section>
      ) : (
        <div className="bank-empty-state compact">
          <span aria-hidden>◌</span>
          <div>
            <h3>Credit check complete</h3>
            <p>Waiting for property price and deposit before calculating affordability.</p>
          </div>
        </div>
      )}
    </div>
  );
}
