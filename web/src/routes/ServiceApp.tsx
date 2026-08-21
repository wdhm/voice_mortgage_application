import { FormEvent, useEffect, useState } from "react";
import { Activity, CheckCircle2, CircleAlert, RotateCcw, ShieldCheck, UserRound, Wifi } from "lucide-react";
import { api, formatSek, jsonRequest, websocketUrl } from "../api";
import type { ServiceCase } from "../types";

type ServiceTab = "case" | "review" | "activity";

export function ServiceApp() {
  const [caseState, setCaseState] = useState<ServiceCase | null>(null);
  const [connected, setConnected] = useState(false);
  const [tab, setTab] = useState<ServiceTab>("review");

  async function refresh() {
    setCaseState(await api<ServiceCase>("/api/service/case"));
  }

  useEffect(() => {
    void refresh();
    const socket = new WebSocket(websocketUrl("service"));
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = () => void refresh();
    return () => socket.close();
  }, []);

  async function reset() {
    if (window.confirm("Reset the complete fictional Emma Lindberg case?")) {
      setCaseState(await api<ServiceCase>("/api/service/reset", jsonRequest("POST")));
    }
  }

  async function approve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const body = {
      employer_name: values.get("employer_name"),
      gross_salary_monthly: Number(values.get("gross_salary_monthly")),
      net_salary_monthly: Number(values.get("net_salary_monthly")),
      employment_type: values.get("employment_type"),
      pay_date: values.get("pay_date"),
      notes: "Reviewed in Bank Alfa service workspace",
    };
    setCaseState(await api<ServiceCase>("/api/service/documents/approve", jsonRequest("POST", body)));
  }

  if (!caseState) return <div className="loading">Loading Bank Alfa Service...</div>;
  const fields = caseState.extracted_income ? Object.entries(caseState.extracted_income) : [];
  const labels: Record<string, string> = {
    employer_name: "Employer",
    gross_salary_monthly: "Gross monthly salary",
    net_salary_monthly: "Net monthly salary",
    employment_type: "Employment",
    pay_date: "Pay date",
  };

  return (
    <div className="service-shell">
      <header className="service-header">
        <div className="brand"><span className="brand-mark">A</span><strong>Bank Alfa Service</strong></div>
        <div className="case-title"><strong>Emma Lindberg</strong><span>Mortgage application</span></div>
        <button className="icon-button" onClick={() => void reset()} title="Reset demo" aria-label="Reset demo"><RotateCcw size={19} /></button>
        <div className="session-state"><Wifi size={16} />{connected ? "Ready" : "Connecting"}</div>
      </header>

      <nav className="mobile-tabs" aria-label="Service workspace">
        {(["case", "review", "activity"] as const).map((item) => <button className={tab === item ? "active" : ""} onClick={() => setTab(item)} key={item}>{item}</button>)}
      </nav>

      <main className="service-grid">
        <aside className={`case-rail panel-${tab}`}>
          <h2>Customer & case</h2>
          <div className="profile-lockup"><UserRound /><div><strong>{caseState.customer_profile.display_name}</strong><span>{caseState.customer_profile.city} · Customer since {caseState.customer_profile.relationship_since}</span></div></div>
          <dl className="details-list">
            <div><dt>Identity</dt><dd>{caseState.identity_status.replaceAll("_", " ")}</dd></div>
            <div><dt>Relationship</dt><dd>{caseState.customer_profile.contact_summary}</dd></div>
            <div><dt>Car loan</dt><dd>{formatSek(caseState.customer_profile.car_loan_balance)} · {formatSek(caseState.customer_profile.car_loan_payment)}/month</dd></div>
            <div><dt>Income evidence</dt><dd>{caseState.document_status.replaceAll("_", " ")}</dd></div>
          </dl>
          <h3>Products</h3>
          {caseState.cards.map((card) => <div className="product-row" key={card.last_four}><span>{card.card_type} · {card.last_four}</span><strong>{card.status}</strong></div>)}
        </aside>

        <section className={`active-work panel-${tab}`}>
          <div className="section-heading"><div><p className="section-kicker">Active work</p><h2>Income review</h2></div><span className={`status-badge ${caseState.document_status === "review_required" ? "review" : "verified"}`}>{caseState.document_status.replaceAll("_", " ")}</span></div>
          {fields.length ? (
            <form onSubmit={approve}>
              <div className="document-review">
                <div className="document-preview"><span>BANK ALFA DEMO</span><h3>Northstar AB</h3><p>Fictional Swedish payslip</p><div className="preview-lines" /></div>
                <div className="field-list">
                  {fields.map(([name, field]) => {
                    const low = field.confidence === null || field.confidence < 0.85;
                    const inputType = name.includes("salary") ? "number" : name === "pay_date" ? "date" : "text";
                    return <label className={low ? "field low" : "field"} key={name}>
                      <span>{labels[name]} <strong>{field.confidence === null ? "No confidence" : `${Math.round(field.confidence * 100)}%`}</strong></span>
                      <input name={name} type={inputType} defaultValue={String(field.value ?? "")} readOnly={caseState.document_status !== "review_required"} />
                      <small>{field.provenance} · {field.grounding}</small>
                    </label>;
                  })}
                </div>
              </div>
              {caseState.document_status === "review_required" && <div className="button-row end"><button className="secondary" type="button" onClick={() => void api("/api/service/documents/reject", jsonRequest("POST")).then(refresh)}>Reject document</button><button className="primary" type="submit"><ShieldCheck size={18} />Approve corrected details</button></div>}
            </form>
          ) : <div className="empty-work">Waiting for Emma to upload a payslip.</div>}

          <div className="work-divider" />
          <div className="section-heading"><div><p className="section-kicker">Mortgage</p><h2>Preliminary assessment</h2></div>{caseState.capacity_result && <span className="status-badge verified">Looks supportable</span>}</div>
          {caseState.capacity_result ? <div className="metric-grid">
            <Metric label="Requested mortgage" value={formatSek(caseState.capacity_result.requested_mortgage)} />
            <Metric label="LTV" value={`${Number(caseState.capacity_result.ltv) * 100}%`} />
            <Metric label="Debt ratio" value={`${caseState.capacity_result.debt_ratio}×`} />
            <Metric label="Monthly amortization" value={formatSek(caseState.capacity_result.total_amortization_monthly)} />
            <Metric label="Stressed KALP surplus" value={formatSek(caseState.capacity_result.kalp_surplus_monthly)} />
            <Metric label="Final decision" value="Advisor required" />
          </div> : <p className="muted">Calculation appears after verified income, consent, and the mock credit check.</p>}
        </section>

        <aside className={`activity-rail panel-${tab}`}>
          <div className="activity-title"><Activity size={19} /><h2>AI activity</h2></div>
          <div className="timeline">
            {[...caseState.events].reverse().map((event) => <div className="timeline-row" key={event.event_id}>
              {event.display.status === "completed" ? <CheckCircle2 size={17} /> : <CircleAlert size={17} />}
              <div><strong>{event.display.label}</strong><span>{event.display.service}</span></div>
              <time>{new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
            </div>)}
            {!caseState.events.length && <p className="muted">No activity yet.</p>}
          </div>
        </aside>
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}