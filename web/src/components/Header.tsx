import type { ConnState } from "../lib/useEventStream";

const CONN_LABEL: Record<ConnState, string> = {
  connecting: "Connecting",
  ready: "Ready",
  reconnecting: "Reconnecting",
  failed: "Disconnected",
};

export function Header({ conn, onReset }: { conn: ConnState; onReset: () => void }) {
  return (
    <header className="header">
      <div className="brand">
        <span className="mark">Bank Alfa</span>
        <span className="sep">·</span>
        <span className="case">Emma Lindberg · Mortgage application</span>
      </div>
      <div className="header-spacer" />
      <span className={`conn ${conn}`} aria-live="polite">
        <span className="dot" />
        {CONN_LABEL[conn]}
      </span>
      <button className="icon-btn" onClick={onReset} title="Start a new application">
        ↺ New application
      </button>
    </header>
  );
}
