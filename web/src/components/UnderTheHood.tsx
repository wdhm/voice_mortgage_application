import type { TimelineEvent } from "../lib/api";

function timeOf(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function TimelineRow({ e }: { e: TimelineEvent }) {
  const { label, status, service } = e.display;
  return (
    <div className={`row ${status}`}>
      <span className="status-icon" aria-hidden />
      <span className="label">
        <span className="op">{label}</span>
        {service ? <span className="svc"> · {service}</span> : null}
      </span>
      <span className="meta">
        <span className="state">{status}</span>
        <span className="time">{timeOf(e.timestamp)}</span>
      </span>
    </div>
  );
}

export function UnderTheHood({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="pane hood">
      <p className="pane-title">Under the hood</p>
      {events.length === 0 ? (
        <p className="timeline-empty">Waiting for activity…</p>
      ) : (
        <div className="timeline">
          {events.map((e) => (
            <TimelineRow key={e.event_id} e={e} />
          ))}
        </div>
      )}
    </div>
  );
}
