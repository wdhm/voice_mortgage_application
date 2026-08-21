const REQUIREMENTS = [
  {
    title: "Personal details",
    description: "Contact details and household information",
    completedBeforeJourney: true,
  },
  {
    title: "Identity verification",
    description: "Identity confirmed securely",
    completedBeforeJourney: true,
  },
  {
    title: "Employment & commitments",
    description: "Employment, expenses and existing loans",
    completedBeforeJourney: true,
  },
  {
    title: "Income documents",
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
];

export function MortgageChecklist({
  activeStep,
  onContinue,
}: {
  activeStep: number;
  onContinue: () => void;
}) {
  const completed = 3 + Math.max(0, activeStep - 1);

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
          const done = item.completedBeforeJourney || (item.step !== undefined && item.step < activeStep);
          const current = item.step === activeStep;
          return (
            <li key={item.title} className={done ? "done" : current ? "current" : "upcoming"}>
              <span className="check-state" aria-hidden>{done ? "✓" : current ? "•" : ""}</span>
              <div>
                <strong>{item.title}</strong>
                <small>{item.description}</small>
              </div>
              <span className="check-label">{done ? "Complete" : current ? "In progress" : "Next"}</span>
            </li>
          );
        })}
      </ol>
      <div className="checklist-action">
        <div>
          <strong>Next: income documents</strong>
          <span>Upload a payslip and review the extracted information.</span>
        </div>
        <button type="button" className="icon-btn primary" onClick={onContinue}>
          Continue application →
        </button>
      </div>
    </section>
  );
}
