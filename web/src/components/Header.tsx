export type AppRole = "customer" | "advisor";

export function Header({ role, onSwitch }: { role: AppRole; onSwitch: (role: AppRole) => void }) {
  const persona =
    role === "advisor"
      ? { name: "Simon", view: "Bank representative view" }
      : { name: "Emma", view: "Customer view" };
  return (
    <header className={`header header--${role}`}>
      <div className="brand">
        <span className="mark">Bank Alfa</span>
      </div>
      <div className="view-persona" role="status" aria-live="polite">
        <span className="view-persona-dot" aria-hidden />
        <span className="view-persona-name">{persona.name}</span>
        <span className="view-persona-sep" aria-hidden>
          ·
        </span>
        <span className="view-persona-view">{persona.view}</span>
      </div>
      <div className="view-switch" role="group" aria-label="Switch view">
        <button
          type="button"
          className={role === "customer" ? "active" : ""}
          aria-pressed={role === "customer"}
          onClick={() => onSwitch("customer")}
        >
          Customer view
        </button>
        <button
          type="button"
          className={role === "advisor" ? "active" : ""}
          aria-pressed={role === "advisor"}
          onClick={() => onSwitch("advisor")}
        >
          Bank view
        </button>
      </div>
    </header>
  );
}
