const REQUIREMENTS = [
  {
    title: "Personal details",
    description: "Contact details and household information",
    completedBeforeJourney: true,
  },
  {
    title: "Identity check",
    description: "Identity confirmed securely",
    completedBeforeJourney: true,
  },
  {
    title: "Income verification",
    description: "Upload a payslip for structured extraction",
    step: 1,
  },
  {
    title: "Credit & affordability",
    description: "Consent, credit check and borrowing capacity",
    step: 2,
  },
  {
    title: "Bank review",
    description: "Advisor reviews the case and makes the final decision",
    step: 3,
  },
  {
    title: "Appointment",
    description: "Meet a mortgage advisor to discuss the application",
    step: 4,
  },
];

export function MortgageChecklist({
  activeStep,
  incomeVerified,
  affordabilityComplete,
  bankReviewComplete,
  appointmentComplete,
  onOpenStep,
}: {
  activeStep: number;
  incomeVerified: boolean;
  affordabilityComplete: boolean;
  bankReviewComplete: boolean;
  appointmentComplete: boolean;
  onOpenStep: (step: number) => void;
}) {
  const completed =
    2 +
    (incomeVerified ? 1 : 0) +
    (affordabilityComplete ? 1 : 0) +
    (bankReviewComplete ? 1 : 0) +
    (appointmentComplete ? 1 : 0);

  return (
    <section className="mortgage-checklist" aria-labelledby="mortgage-checklist-title">
      <div className="checklist-heading">
        <div>
          <p className="eyebrow">Your application</p>
          <h1 id="mortgage-checklist-title">Steps to a mortgage decision</h1>
          <p>
            Complete each step before a Bank Alfa advisor can make the final lending decision.
          </p>
        </div>
        <div className="checklist-progress" aria-label={`${completed} of 6 steps complete`}>
          <strong>{completed}/6</strong>
          <span>complete</span>
        </div>
      </div>
      <ol>
        {REQUIREMENTS.map((item) => {
          const done =
            item.completedBeforeJourney ||
            (item.step === 1
              ? incomeVerified
              : item.step === 2
                ? affordabilityComplete
                : item.step === 3
                  ? bankReviewComplete
                  : item.step === 4
                    ? appointmentComplete
                    : false);
          const current = !done && item.step === activeStep;
          const openable =
            item.step === 1 ||
            (item.step === 2 && incomeVerified) ||
            (item.step === 3 && affordabilityComplete) ||
            (item.step === 4 && bankReviewComplete);
          const className = done ? "done" : current ? "current" : "upcoming";
          const body = (
            <>
              <span className="check-state" aria-hidden>{done ? "✓" : current ? "•" : ""}</span>
              <div>
                <strong>{item.title}</strong>
                <small>{item.description}</small>
              </div>
              <span className="check-label">{done ? "Complete" : current ? "In progress" : "Open"}</span>
            </>
          );
          return (
            <li key={item.title} className={className}>
              {openable ? (
                <button type="button" className="checklist-step" onClick={() => onOpenStep(item.step!)}>
                  {body}
                </button>
              ) : (
                <div className="checklist-step static">{body}</div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

const APPLICATION_STAGES = [
  { step: 1, title: "Income verification" },
  { step: 2, title: "Credit & affordability" },
  { step: 3, title: "Bank review" },
  { step: 4, title: "Appointment" },
];

export function MortgageProgress({
  activeStep,
  incomeVerified,
  affordabilityComplete,
  bankReviewComplete,
  appointmentComplete,
  onOpenStep,
}: {
  activeStep: number;
  incomeVerified: boolean;
  affordabilityComplete: boolean;
  bankReviewComplete: boolean;
  appointmentComplete: boolean;
  onOpenStep: (step: number) => void;
}) {
  const completed = [incomeVerified, affordabilityComplete, bankReviewComplete, appointmentComplete];

  return (
    <nav className="mortgage-progress" aria-label="Mortgage application progress">
      <div className="mortgage-progress-heading">
        <strong>Application progress</strong>
        <span>Step {activeStep} of 4</span>
      </div>
      <ol>
        {APPLICATION_STAGES.map((stage, index) => {
          const done = completed[index];
          const current = stage.step === activeStep;
          const unlocked =
            stage.step === 1 ||
            (stage.step === 2 && incomeVerified) ||
            (stage.step === 3 && affordabilityComplete) ||
            (stage.step === 4 && bankReviewComplete);
          return (
            <li
              key={stage.step}
              className={`${done ? "complete" : "incomplete"} ${current ? "active" : ""}`}
              aria-current={current ? "step" : undefined}
            >
              <button type="button" onClick={() => onOpenStep(stage.step)} disabled={!unlocked}>
                <span className="progress-check" aria-hidden>{done ? "✓" : stage.step}</span>
                <span>
                  <strong>{stage.title}</strong>
                  <small>{done ? "Complete" : current ? "In progress" : unlocked ? "Ready" : "Locked"}</small>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
