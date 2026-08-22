import { useEffect, useState } from "react";
import { getCase, type CapacityMetrics, type DemoCaseView } from "../lib/api";

const kr = (n: number | undefined | null) =>
  n === undefined || n === null ? "—" : `${n.toLocaleString("sv-SE")} kr`;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="sum-section">
      <p className="sum-title">{title}</p>
      {children}
    </div>
  );
}

function Row({ k, v, strong }: { k: string; v: React.ReactNode; strong?: boolean }) {
  return (
    <div className={`sum-row ${strong ? "strong" : ""}`}>
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

function CapacityBreakdown({ m }: { m: CapacityMetrics }) {
  return (
    <table className="kalp">
      <tbody>
        <Kalp k="Net income (monthly)" v={kr(m.total_monthly_costs + m.kalp_surplus_monthly)} plus />
        <Kalp k="Amortisation (3%)" v={`− ${kr(m.total_amort_monthly)}`} />
        <Kalp k="Stressed interest (net)" v={`− ${kr(m.stressed_net_interest_monthly)}`} />
        <Kalp k="Living costs" v={`− ${kr(m.living_cost_monthly)}`} />
        <Kalp k="Property running costs" v={`− ${kr(m.property_running_cost_monthly)}`} />
        <Kalp k="Existing car loan" v={`− ${kr(m.existing_debt_payment_monthly)}`} />
        <tr className="kalp-total">
          <td>Monthly surplus (KALP)</td>
          <td>{kr(m.kalp_surplus_monthly)}</td>
        </tr>
      </tbody>
    </table>
  );
}

function Kalp({ k, v, plus }: { k: string; v: string; plus?: boolean }) {
  return (
    <tr className={plus ? "plus" : ""}>
      <td>{k}</td>
      <td>{v}</td>
    </tr>
  );
}

/**
 * Screen 3 — the advisor handoff. Server-owned status text; never renders
 * "Approved" for the mortgage. Re-fetches the case whenever the timeline advances.
 */
export function SummaryPanel({
  refreshKey,
  audience = "advisor",
  onContinue,
}: {
  refreshKey: number;
  audience?: "customer" | "advisor";
  onContinue?: () => void;
}) {
  const [c, setC] = useState<DemoCaseView | null>(null);

  useEffect(() => {
    getCase().then(setC).catch(() => {});
  }, [refreshKey]);

  const s = c?.advisor_summary;
  if (!c || !s) {
    return (
      <div className="summary-panel">
        <div className="sum-head">
          <h2>Advisor summary</h2>
        </div>
        <p className="doc-sub">
          The structured handoff appears here once the voice assessment is complete.
        </p>
      </div>
    );
  }

  const sec = s.sections;
  const loan = (sec.requested_loan ?? {}) as Record<string, number | string>;
  const credit = (sec.credit_result ?? {}) as Record<string, number | string>;
  const commitments = Array.isArray(sec.credit_result?.existingCommitments)
    ? sec.credit_result.existingCommitments
    : [];
  const carLoan = (commitments[0] ?? {}) as Record<string, number | string>;
  const m = sec.capacity_metrics;
  const card = c.cards[0];
  const flagged = s.flags.includes("dti_above_guideline");

  if (audience === "customer") {
    return (
      <div className="customer-review-panel">
        <div className="customer-review-status">
          <span aria-hidden>✓</span>
          <div>
            <p className="eyebrow">Case package prepared</p>
            <h2>Ready for bank review</h2>
            <p>Your verified income and affordability assessment have been sent to a mortgage advisor.</p>
          </div>
        </div>
        <div className="customer-review-steps">
          <div><span>✓</span><div><strong>Income verified</strong><small>Payslip details accepted</small></div></div>
          <div><span>✓</span><div><strong>Affordability assessed</strong><small>7% stress test completed</small></div></div>
          <div className={flagged ? "note" : ""}>
            <span>{flagged ? "!" : "✓"}</span>
            <div>
              <strong>{flagged ? "Advisor note included" : "Within DTI guideline"}</strong>
              <small>{flagged ? "The advisor will review the debt-to-income ratio" : "No DTI exception was flagged"}</small>
            </div>
          </div>
        </div>
        <p className="handoff-note">
          This is not a final lending decision. A Bank Alfa advisor reviews the application.
        </p>
        {onContinue && (
          <div className="journey-next">
            <span>Next, arrange a time to speak with your mortgage advisor.</span>
            <button type="button" className="icon-btn primary" onClick={onContinue}>
              Continue to appointment →
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="summary-panel">
      <div className="sum-head">
        <h2>Advisor summary</h2>
        <span className="mode">Human handoff</span>
      </div>

      <div className={`status-banner ${flagged ? "warn" : "ok"}`}>
        <strong>{s.status_text}</strong>
        <span>{s.decision_text}</span>
      </div>

      <div className="sum-grid">
        <Section title="Customer & identity">
          <Row k="Customer" v={sec.identity?.customer ?? c.customer_profile.display_name} />
          <Row k="Customer status" v={c.identity_status === "identified" ? "Known customer" : c.identity_status} />
          <Row k="Assurance" v={sec.identity?.assurance ?? "High"} />
        </Section>

        <Section title="Verified income">
          <Row k="Employer" v={sec.income_provenance?.employer ?? "—"} />
          <Row k="Gross (monthly)" v={kr(sec.income_provenance?.gross_monthly)} />
          <Row k="Net (monthly)" v={kr(sec.income_provenance?.net_monthly)} />
          <Row k="Provenance" v={sec.income_provenance?.provenance ?? "—"} />
        </Section>

        <Section title="Property & requested mortgage">
          <Row k="Location" v={(loan.location as string) ?? "—"} />
          <Row k="Purchase price" v={kr(loan.purchase_price as number)} />
          <Row k="Deposit" v={kr(loan.deposit as number)} />
          <Row k="Requested mortgage" v={kr(m?.requested_mortgage)} strong />
          <Row k="Loan-to-value" v={m ? `${m.ltv_pct}%` : "—"} />
          <Row k="Debt-to-income" v={m ? `${m.dti_ratio}×` : "—"} />
        </Section>

        <Section title="Credit & existing debt">
          <Row k="Credit score" v={credit.creditScore != null ? `${credit.creditScore} / ${credit.maxScore}` : "—"} />
          <Row k="Risk band" v={(credit.riskBand as string) ?? "—"} />
          <Row k="Existing car loan" v={kr(carLoan.balance as number)} />
          <Row k="Car loan payment" v={kr(carLoan.monthlyPayment as number)} />
          <Row k="Payment remarks" v={Array.isArray(credit.paymentRemarks) && credit.paymentRemarks.length ? credit.paymentRemarks.join(", ") : "None"} />
        </Section>

        {m && (
          <Section title="Affordability (stressed KALP)">
            <CapacityBreakdown m={m} />
          </Section>
        )}

        <Section title="Meeting & card incident">
          {c.booked_meeting ? (
            <>
              <Row k="Advisor meeting" v={new Date(c.booked_meeting.slot.start).toLocaleString("sv-SE")} />
              <Row k="Reference" v={c.booked_meeting.booking_reference} />
            </>
          ) : (
            <Row k="Advisor meeting" v="Not booked" />
          )}
          {card && (
            <Row
              k={`Card ·${card.last_four}`}
              v={card.status === "blocked" || card.status === "replacement_ordered" ? "Blocked" : "Active"}
            />
          )}
          {c.replacement_order && <Row k="Replacement" v={c.replacement_order.delivery_estimate} />}
        </Section>
      </div>

      {sec.risks_caveats && sec.risks_caveats.length > 0 && (
        <div className="caveats">
          <p className="sum-title">Caveats & missing evidence</p>
          <ul>
            {sec.risks_caveats.map((cv, i) => (
              <li key={i}>{cv}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="handoff-note">
        This is a preliminary, illustrative assessment. A Bank Alfa advisor owns the final lending decision.
      </p>
      {onContinue && (
        <div className="journey-next">
          <span>Continue to arrange the advisor appointment.</span>
          <button type="button" className="icon-btn primary" onClick={onContinue}>
            Continue to appointment →
          </button>
        </div>
      )}
    </div>
  );
}
