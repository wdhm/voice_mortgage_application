import { useEffect, useRef } from "react";
import { useVoice } from "../lib/useVoice";

// Canonical customer utterances for the pre-recorded demo — clicking sends the
// real transcript to the server, which classifies consent and drives the tools.
const BEATS = [
  "I want a mortgage pre-approval for a house in Täby, around seven million kronor.",
  "Yes, you can run the credit check.",
  "I have one million seven hundred and fifty thousand kronor deposit.",
  "I'm away for three weeks. Do you have anything after that?",
  "Monday the 21st of September at 15:00 works.",
  "One more thing — my card was stolen.",
  "Yes, block it and order a replacement.",
];

const ACTION_LABELS: Record<string, string> = {
  credit_check: "run a credit check (UC)",
  block_card: "block the card and order a replacement",
};

export function VoicePanel() {
  const v = useVoice();
  const textRef = useRef<HTMLInputElement | null>(null);
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [v.transcript.length]);

  const sendText = (text: string) => {
    const t = text.trim();
    if (!t) return;
    v.send({ type: "text", text: t });
  };

  const consentOpen = v.consent?.status === "requested";

  return (
    <div className="voice-panel">
      <div className="voice-head">
        <h2>Voice application</h2>
        <span className={`mode ${v.provider}`}>
          {v.provider === "foundry" ? "Foundry Voice Live" : "Simulated voice"}
        </span>
      </div>
      <p className="doc-sub">
        Emma speaks with the Bank Alfa assistant. Identity, consent and every credit
        action are gated server-side — the model can only ask.
      </p>

      {v.conn === "reconnecting" && (
        <div className="reconnecting" role="status">
          <span className="consent-dot" /> Reconnecting to the voice channel…
        </div>
      )}

      {v.session === "idle" ? (
        <button className="icon-btn primary" onClick={() => v.send({ type: "start" })}>
          Start voice conversation
        </button>
      ) : (
        <button className="icon-btn subtle" onClick={() => v.send({ type: "stop" })}>
          End conversation
        </button>
      )}

      {v.digitald === "requested" && (
        <div className="digitald-modal">
          <div className="dd-body">
            <strong>DigitalD identity request</strong>
            <p>Emma is authenticating with BankID / DigitalD. Approve to continue.</p>
            <button className="icon-btn primary" onClick={() => v.send({ type: "digitald_approve" })}>
              Approve identity
            </button>
          </div>
        </div>
      )}

      {consentOpen && v.consent && (
        <div className="consent-prompt">
          <span className="consent-dot" />
          <div>
            <strong>Consent requested</strong>
            <p>
              The assistant asked permission to {ACTION_LABELS[v.consent.action] ?? v.consent.action}
              {v.consent.scope ? ` (${v.consent.scope})` : ""}. It will proceed only on a clear “yes”.
            </p>
          </div>
        </div>
      )}
      {v.consent && v.consent.status !== "requested" && (
        <div className={`consent-result ${v.consent.status}`}>
          Consent {v.consent.status} for {ACTION_LABELS[v.consent.action] ?? v.consent.action}.
        </div>
      )}

      <div className="transcript" ref={logRef}>
        {v.transcript.length === 0 && <p className="empty">Transcript will appear here.</p>}
        {v.transcript.map((l, i) => (
          <div key={i} className={`line ${l.who}`}>
            <span className="who">{l.who === "agent" ? "Assistant" : "Emma"}</span>
            <span className="text">{l.text}</span>
          </div>
        ))}
      </div>

      {v.session === "active" && v.digitald === "approved" && (
        <div className="say-controls">
          <div className="beats">
            {BEATS.map((b, i) => (
              <button key={i} className="beat" onClick={() => sendText(b)} title={b}>
                {b.length > 46 ? `${b.slice(0, 44)}…` : b}
              </button>
            ))}
          </div>
          <form
            className="say-input"
            onSubmit={(e) => {
              e.preventDefault();
              if (textRef.current) {
                sendText(textRef.current.value);
                textRef.current.value = "";
              }
            }}
          >
            <input ref={textRef} placeholder="Type what Emma says…" />
            <button className="icon-btn" type="submit">
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
