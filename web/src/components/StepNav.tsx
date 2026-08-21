const STEPS = [
  { n: 1, label: "Documents" },
  { n: 2, label: "Affordability call" },
  { n: 3, label: "Bank review" },
];

export function StepNav({ active, onGo }: { active: number; onGo?: (n: number) => void }) {
  return (
    <nav className="steps" aria-label="Application progress">
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
