export type AppRole = "customer" | "advisor";

export function Header({ role, onSwitch }: { role: AppRole; onSwitch: (role: AppRole) => void }) {
  return (
    <header className="header">
      <div className="brand">
        <span className="mark">Bank Alfa</span>
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
