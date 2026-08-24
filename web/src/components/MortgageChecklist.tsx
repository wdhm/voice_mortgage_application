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
    title: "Credit check",
    description: "Credit assessment completed and approved",
    completedBeforeJourney: true,
  },
  {
    title: "Income verification",
    description: "Upload a payslip for structured extraction",
    step: 2,
  },
  {
    title: "Appointment",
    description: "Meet a mortgage advisor to discuss the application",
    step: 3,
  },
];

export function MortgageChecklist({
  activeStep,
  incomeVerified,
  appointmentComplete,
  onOpenStep,
}: {
  activeStep: number;
  incomeVerified: boolean;
  appointmentComplete: boolean;
  onOpenStep: (step: number) => void;
}) {
  const completed =
    3 +
    (incomeVerified ? 1 : 0) +
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
        <div className="checklist-progress" aria-label={`${completed} of 5 steps complete`}>
          <strong>{completed}/5</strong>
          <span>complete</span>
        </div>
      </div>
      <ol>
        {REQUIREMENTS.map((item) => {
          const done =
            item.completedBeforeJourney ||
            (item.step === 2
              ? incomeVerified
              : item.step === 3
                ? appointmentComplete
                : false);
          const current = !done && item.step === activeStep;
          const openable = item.step === 2 || item.step === 3;
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
  { step: 1, title: "Credit check" },
  { step: 2, title: "Income verification" },
  { step: 3, title: "Appointment" },
];

export function MortgageProgress({
  activeStep,
  incomeVerified,
  appointmentComplete,
  onOpenStep,
}: {
  activeStep: number;
  incomeVerified: boolean;
  appointmentComplete: boolean;
  onOpenStep: (step: number) => void;
}) {
  return (
    <nav className="mortgage-progress" aria-label="Mortgage application progress">
      <div className="mortgage-progress-heading">
        <strong>Application progress</strong>
        <span>Step {activeStep} of 3</span>
      </div>
      <ol>
        {APPLICATION_STAGES.map((stage) => {
          const done =
            stage.step === 1 ||
            (stage.step === 2 && incomeVerified) ||
            (stage.step === 3 && appointmentComplete);
          const current = stage.step === activeStep;
          const unlocked = stage.step === 2 || stage.step === 3;
          return (
            <li
              key={stage.step}
              className={`${done ? "complete" : "incomplete"} ${current ? "active" : ""}`}
              aria-current={current ? "step" : undefined}
            >
              <button type="button" onClick={() => onOpenStep(stage.step)} disabled={!unlocked || stage.step === 1}>
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
