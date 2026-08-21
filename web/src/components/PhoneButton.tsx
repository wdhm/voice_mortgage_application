import type { VoiceStreamState } from "../lib/useVoice";

export function PhoneButton({ voice }: { voice: VoiceStreamState }) {
  const active = voice.session === "active";
  const unavailable = !active && (voice.conn !== "ready" || voice.starting);

  const toggleCall = () => {
    if (unavailable) return;
    if (active) voice.stop();
    else void voice.start();
  };

  return (
    <div className="phone-control">
      {voice.error && (
        <div className="phone-notice error" role="alert">
          <strong>Call unavailable</strong>
          <span>{voice.error}</span>
        </div>
      )}
      <button
        type="button"
        className={`phone-button ${active ? "active" : ""}`}
        onClick={toggleCall}
        disabled={unavailable}
        aria-label={active ? "End voice session" : "Start voice session"}
        aria-pressed={active}
        title={active ? "End voice session" : "Call Bank Alfa"}
      >
        <svg viewBox="0 0 24 24" aria-hidden>
          <path
            d="M7.2 3.4 9.5 8 7.7 9.8c1.1 2.2 2.9 4 5.1 5.1l1.8-1.8 4.6 2.3-.5 3.4c-.1.8-.8 1.4-1.6 1.4C9.8 20.2 3.8 14.2 3.8 6.9c0-.8.6-1.5 1.4-1.6l2-.3Z"
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.8"
          />
        </svg>
        <span>{voice.starting ? "Connecting…" : active ? "End call" : "Call us"}</span>
      </button>
    </div>
  );
}
