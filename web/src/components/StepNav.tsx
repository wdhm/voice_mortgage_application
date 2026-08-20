const STEPS = [
  { n: 1, label: "Income document" },
  { n: 2, label: "Voice application" },
  { n: 3, label: "Advisor summary" },
];

export function StepNav({ active }: { active: number }) {
  return (
    <nav className="steps" aria-label="Demo progress">
      {STEPS.map((s) => (
        <div key={s.n} className={`step ${s.n === active ? "active" : ""}`}>
          <span className="num">{s.n}</span>
          {s.label}
        </div>
      ))}
    </nav>
  );
}
