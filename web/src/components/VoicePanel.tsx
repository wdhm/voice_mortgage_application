import { useEffect, useRef, useState, type RefObject } from "react";
import {
  approveAndFetchCreditReport,
  getCase,
  type AdvisorSummary,
  type CapacityMetrics,
  type DemoCaseView,
} from "../lib/api";
import type { VoiceStreamState } from "../lib/useVoice";
import { isSpeechEnabled, setSpeechEnabled } from "../lib/speech";

export function VoicePanel({
  v,
  refreshKey = 0,
  title = "Digital mortgage assistant",
  description = "Complete the credit and affordability assessment in a secure conversation.",
  onContinue,
  showAssessment = true,
}: {
  v: VoiceStreamState;
  refreshKey?: number;
  title?: string;
  description?: string;
  onContinue?: () => void;
  showAssessment?: boolean;
}) {
  const logRef = useRef<HTMLDivElement>(null);
  const [voiceOn, setVoiceOn] = useState(isSpeechEnabled());
  const [capacity, setCapacity] = useState<CapacityMetrics | null>(null);
  const [summary, setSummary] = useState<AdvisorSummary | null>(null);
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);
  const [creditFlow, setCreditFlow] = useState<
    "idle" | "authorizing" | "fetching" | "analyzing" | "complete" | "error"
  >("idle");
  const [creditError, setCreditError] = useState<string | null>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [v.transcript.length]);

  useEffect(() => {
    getCase()
      .then((caseView) => {
        setCaseView(caseView);
        setCapacity(caseView.capacity_result?.metrics ?? null);
        setSummary(caseView.advisor_summary);
        if (caseView.credit_result) setCreditFlow("complete");
      })
      .catch(() => {});
  }, [refreshKey, v.transcript.length]);

  const toggleVoice = () => {
    const next = !voiceOn;
    setVoiceOn(next);
    setSpeechEnabled(next);
  };

  const consentOpen = v.consent?.status === "requested";
  const consentComplete =
    caseView?.credit_result !== null ||
    v.consent?.status === "granted" ||
    v.consent?.status === "consumed";
  const creditComplete = caseView?.credit_result !== null && caseView !== null;
  const active = v.session === "active";

  const approveCreditCheck = async () => {
    setCreditError(null);
    setCreditFlow("authorizing");
    try {
      await delay(450);
      setCreditFlow("fetching");
      const request = approveAndFetchCreditReport();
      await Promise.all([request, delay(950)]);
      setCreditFlow("analyzing");
      await delay(850);
      const nextCase = await getCase();
      setCaseView(nextCase);
      setCapacity(nextCase.capacity_result?.metrics ?? null);
      setSummary(nextCase.advisor_summary);
      setCreditFlow("complete");
    } catch (error) {
      setCreditError(error instanceof Error ? error.message : "Unable to retrieve the credit report.");
      setCreditFlow("error");
    }
  };

  if (!showAssessment) {
    return (
      <div className="voice-panel appointment-voice-panel">
        <div className="voice-head">
          <div>
            <p className="eyebrow">{active ? "Voice live" : "Voice service"}</p>
            <h2>{title}</h2>
          </div>
          <VoiceToggle voiceOn={voiceOn} onToggle={toggleVoice} />
        </div>
        <p className="doc-sub">{description}</p>
        <CallStatus active={active} />
        <Transcript transcript={v.transcript} logRef={logRef} />
      </div>
    );
  }

  return (
    <div className="credit-experience">
      <section className="credit-hero">
        <span className="credit-hero-icon" aria-hidden>
          <svg viewBox="0 0 24 24">
            <path d="M12 3 19 6v5c0 4.6-2.9 8-7 10-4.1-2-7-5.4-7-10V6l7-3Z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        </span>
        <div>
          <p className="eyebrow">Secure credit assessment</p>
          <h2>Let’s check your borrowing position</h2>
          <p>
            We’ll confirm your consent, retrieve a credit report, and calculate affordability using
            your verified income. It usually takes about two minutes.
          </p>
        </div>
        <span className="credit-time">About 2 min</span>
      </section>

      <div className="credit-workspace">
        <section className="credit-checklist-card">
          <div className="credit-card-heading">
            <div>
              <p className="eyebrow">Assessment steps</p>
              <h3>What we’ll check</h3>
            </div>
            <span>{capacity ? "Complete" : "In progress"}</span>
          </div>
          <AssessmentStep
            number={1}
            title="Your consent"
            detail="Permission to request credit information"
            state={consentComplete ? "complete" : "current"}
          />
          {!consentComplete && (
            <div className="consent-approval">
              <p>
                By approving, you allow Bank Alfa to request a mock credit report for this
                application.
              </p>
              <button
                type="button"
                className="consent-approve-button"
                onClick={() => void approveCreditCheck()}
                disabled={creditFlow !== "idle" && creditFlow !== "error"}
              >
                {creditFlow === "idle" || creditFlow === "error" ? "Approve" : "Processing…"}
              </button>
            </div>
          )}
          {creditFlow !== "idle" && <CreditFetchProgress state={creditFlow} error={creditError} />}
          <AssessmentStep
            number={2}
            title="Credit report"
            detail={creditComplete ? `${caseView.credit_result?.risk_band} risk profile` : "Score, remarks, and commitments"}
            state={creditComplete ? "complete" : consentComplete ? "current" : "pending"}
          />
          <AssessmentStep
            number={3}
            title="Affordability"
            detail={capacity ? "Stress test and borrowing capacity calculated" : "Income, deposit, and monthly commitments"}
            state={capacity ? "complete" : creditComplete ? "current" : "pending"}
          />
          <div className="credit-data-note">
            <span aria-hidden>✓</span>
            <div>
              <strong>Income already verified</strong>
              <small>Your approved payslip information will be used automatically.</small>
            </div>
          </div>
        </section>

        <section className="credit-method-card">
          <div className="credit-method-head">
            <div>
              <p className="eyebrow">Borrowing calculation</p>
              <h3>How your position is checked</h3>
            </div>
            <span className="method-rate">7% stress rate</span>
          </div>
          <p className="credit-method-copy">
            During the call, we combine verified information with the property details you provide.
          </p>
          <div className="calculation-inputs">
            <div>
              <span aria-hidden>1</span>
              <div><strong>Verified income</strong><small>Gross and net salary from your approved payslip</small></div>
            </div>
            <div>
              <span aria-hidden>2</span>
              <div><strong>Property and deposit</strong><small>Purchase price and available deposit from you</small></div>
            </div>
            <div>
              <span aria-hidden>3</span>
              <div><strong>Existing commitments</strong><small>Debt and monthly payments from the consented credit check</small></div>
            </div>
            <div>
              <span aria-hidden>4</span>
              <div><strong>Stress-tested budget</strong><small>7% interest stress, amortization, and estimated living costs</small></div>
            </div>
          </div>
          <div className="calculation-output">
            <span aria-hidden>→</span>
            <div>
              <strong>Your preliminary borrowing position</strong>
              <small>LTV, monthly surplus, and debt-to-income ratio for advisor review</small>
            </div>
          </div>

          {v.conn === "reconnecting" && (
            <div className="reconnecting" role="status">
              <span className="consent-dot" /> Reconnecting to the secure channel…
            </div>
          )}

          {consentOpen && !creditComplete && v.consent && (
            <div className="consent-prompt">
              <span className="consent-dot" />
              <div>
                <strong>Your permission is needed</strong>
                <p>
                  Please answer “yes” if you allow Bank Alfa to run a credit check for this
                  mortgage application.
                </p>
              </div>
            </div>
          )}
          {v.consent && v.consent.status !== "requested" && (
            <div className={`consent-result ${v.consent.status}`}>
              <span aria-hidden>✓</span>
              Credit-check consent {v.consent.status}.
            </div>
          )}

          <CallStatus active={active} complete={Boolean(capacity)} />
          <div className="credit-method-tools">
            <span>Use the Call us button to start or end the conversation.</span>
            <VoiceToggle voiceOn={voiceOn} onToggle={toggleVoice} />
          </div>
          <Transcript transcript={v.transcript} logRef={logRef} compact />
          <p className="credit-security">
            <span aria-hidden>▣</span> Encrypted connection · consent is recorded for this application only
          </p>
        </section>
      </div>

      {capacity && <AffordabilityCard metrics={capacity} />}
      {summary && <AdvisorHandoffCard summary={summary} />}
      {summary && onContinue && (
        <div className="journey-next">
          <span>Your affordability assessment is ready for bank review.</span>
          <button type="button" className="icon-btn primary" onClick={onContinue}>
            Continue to bank review →
          </button>
        </div>
      )}
    </div>
  );
}

const CREDIT_FLOW_ORDER = ["authorizing", "fetching", "analyzing", "complete"] as const;

function CreditFetchProgress({
  state,
  error,
}: {
  state: "authorizing" | "fetching" | "analyzing" | "complete" | "error";
  error: string | null;
}) {
  if (state === "error") {
    return <div className="credit-fetch-error" role="alert">{error}</div>;
  }
  const current = CREDIT_FLOW_ORDER.indexOf(state);
  const stages = [
    ["Consent recorded", "Securing your approval"],
    ["Contacting credit bureau", "Retrieving the mock credit file"],
    ["Analyzing report", "Checking score, remarks, and commitments"],
    ["Credit report ready", "Assessment can continue"],
  ];
  return (
    <div className="credit-fetch-progress" role="status" aria-live="polite">
      <div className="credit-fetch-progress-head">
        <strong>Credit report progress</strong>
        <span>{state === "complete" ? "Complete" : "Working securely…"}</span>
      </div>
      {stages.map(([title, detail], index) => {
        const status = index < current || state === "complete"
          ? "complete"
          : index === current
            ? "active"
            : "pending";
        return (
          <div className={`credit-fetch-stage ${status}`} key={title}>
            <span aria-hidden>{status === "complete" ? "✓" : index + 1}</span>
            <div><strong>{title}</strong><small>{detail}</small></div>
            {status === "active" && <i aria-hidden />}
          </div>
        );
      })}
    </div>
  );
}

const delay = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function AssessmentStep({
  number,
  title,
  detail,
  state,
}: {
  number: number;
  title: string;
  detail: string;
  state: "complete" | "current" | "pending";
}) {
  return (
    <div className={`assessment-step ${state}`}>
      <span className="assessment-step-marker" aria-hidden>{state === "complete" ? "✓" : number}</span>
      <div>
        <strong>{title}</strong>
        <small>{detail}</small>
      </div>
      <em>{state === "complete" ? "Done" : state === "current" ? "Current" : "Next"}</em>
    </div>
  );
}

function VoiceToggle({ voiceOn, onToggle }: { voiceOn: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      className={`voice-toggle ${voiceOn ? "on" : "off"}`}
      onClick={onToggle}
      aria-pressed={voiceOn}
      title={voiceOn ? "Assistant voice on — click to mute" : "Assistant voice muted — click to enable"}
    >
      {voiceOn ? "Voice on" : "Muted"}
    </button>
  );
}

function CallStatus({
  active,
  complete = false,
}: {
  active: boolean;
  complete?: boolean;
}) {
  return (
    <div className={`call-status ${active ? "live" : complete ? "complete" : "idle"}`}>
      <span className="call-status-icon" aria-hidden>{active ? "●" : complete ? "✓" : "○"}</span>
      <div>
        <strong>{active ? "Voice live" : complete ? "Assessment complete" : "Ready to begin"}</strong>
        <small>
          {active
            ? "The secure voice session is active. Speak naturally."
            : complete
              ? "Your result is ready below."
              : "Press Call us in the lower-right corner when you’re ready."}
        </small>
      </div>
    </div>
  );
}

function Transcript({
  transcript,
  logRef,
  compact = false,
}: {
  transcript: VoiceStreamState["transcript"];
  logRef: RefObject<HTMLDivElement>;
  compact?: boolean;
}) {
  return (
    <div className={`transcript ${compact ? "compact" : ""}`} ref={logRef}>
      {transcript.length === 0 && (
        <p className="empty">Your secure conversation will appear here.</p>
      )}
      {transcript.map((line, index) => (
        <div key={index} className={`line ${line.who}`}>
          <span className="who">{line.who === "agent" ? "Bank Alfa assistant" : "You"}</span>
          <span className="text">{line.text}</span>
        </div>
      ))}
    </div>
  );
}

const sek = (value: number) => `SEK ${value.toLocaleString("sv-SE")}/mo`;

function AffordabilityCard({ metrics }: { metrics: CapacityMetrics }) {
  const flagged = metrics.dti_flag === "above_soft_guideline";
  return (
    <section className={`affordability-card ${flagged ? "warning" : ""}`}>
      <div className="affordability-card-head">
        <div>
          <p className="pane-title">Affordability check</p>
          <span>Preliminary stress-test result</span>
        </div>
        <span className={`assessment-chip ${flagged ? "warning" : "ok"}`}>
          {flagged ? "Advisor note" : "Within guideline"}
        </span>
      </div>
      <dl className="affordability-metrics">
        <div><dt>LTV</dt><dd>{metrics.ltv_pct}%</dd></div>
        <div><dt>Amortization</dt><dd>{metrics.amortization_tier}</dd></div>
        <div><dt>Stress rate</dt><dd>{Math.round(metrics.stress_test_rate * 100)}%</dd></div>
        <div><dt>Net after stress</dt><dd>{sek(metrics.net_after_stress)}</dd></div>
        <div className={flagged ? "metric-warning" : ""}>
          <dt>DTI</dt>
          <dd>
            {metrics.dti_ratio}x
            {flagged && <small>⚠ above 4.5x guideline</small>}
          </dd>
        </div>
      </dl>
      <p className="preliminary-note">A human advisor makes the final lending decision.</p>
    </section>
  );
}

function AdvisorHandoffCard({ summary }: { summary: AdvisorSummary }) {
  return (
    <section className="advisor-handoff-card">
      <p className="pane-title">Advisor summary</p>
      <p>{summary.summary}</p>
      <div>
        <span>Flags: {summary.flags.length ? summary.flags.join(", ") : "None"}</span>
        <span>Recommended action: {summary.recommended_action.replace("_", " ")}</span>
      </div>
    </section>
  );
}
