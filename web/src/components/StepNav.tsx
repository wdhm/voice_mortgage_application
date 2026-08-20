const STEPS = [
  { n: 1, label: "Income document" },
  { n: 2, label: "Voice application" },
  { n: 3, label: "Advisor summary" },
];

export function StepNav({ active, onGo }: { active: number; onGo?: (n: number) => void }) {
  return (
    <nav className="steps" aria-label="Demo progress">
      {STEPS.map((s) => (
        <button
          key={s.n}
          type="button"
          className={`step ${s.n === active ? "active" : ""} ${s.n < active ? "done" : ""}`}
          onClick={() => onGo?.(s.n)}
          aria-current={s.n === active ? "step" : undefined}
        >
          <span className="num">{s.n < active ? "✓" : s.n}</span>
          {s.label}
        </button>
      ))}
    </nav>
  );
}
