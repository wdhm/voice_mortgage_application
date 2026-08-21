import { useEffect, useRef, useState } from "react";
import type { VoiceStreamState } from "../lib/useVoice";
import { isSpeechEnabled, primeAudio, setSpeechEnabled } from "../lib/speech";

const ACTION_LABELS: Record<string, string> = {
  credit_check: "run a credit check (UC)",
  block_card: "block the card and order a replacement",
};

export function VoicePanel({ v }: { v: VoiceStreamState }) {
  const logRef = useRef<HTMLDivElement | null>(null);
  const [voiceOn, setVoiceOn] = useState(isSpeechEnabled());

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [v.transcript.length]);

  const toggleVoice = () => {
    const next = !voiceOn;
    setVoiceOn(next);
    setSpeechEnabled(next);
  };

  const consentOpen = v.consent?.status === "requested";
  const active = v.session === "active";
  const listening = active && v.digitald === "approved";
  const micState = listening ? "listening" : active ? "active" : "idle";

  return (
    <div className="voice-panel">
      <div className="voice-head">
        <h2>Advisor call</h2>
        <div className="voice-head-meta">
          <button
            type="button"
            className={`voice-toggle ${voiceOn ? "on" : "off"}`}
            onClick={toggleVoice}
            aria-pressed={voiceOn}
            title={voiceOn ? "Assistant voice on — click to mute" : "Assistant voice muted — click to enable"}
          >
            {voiceOn ? "🔊 Voice on" : "🔇 Muted"}
          </button>
          <span className="live-tag">
            <span className="live-dot" /> Live
          </span>
        </div>
      </div>
      <p className="doc-sub">
        Talk to your Bank Alfa advisor. Every credit action is carried out only after you
        confirm it out loud.
      </p>

      {v.conn === "reconnecting" && (
        <div className="reconnecting" role="status">
          <span className="consent-dot" /> Reconnecting to the voice channel…
        </div>
      )}

      <div className={`voice-live ${micState}`}>
        <button
          type="button"
          className="mic"
          onClick={() => {
            if (!active) primeAudio();
            v.send({ type: active ? "stop" : "start" });
          }}
          title={active ? "End the voice conversation" : "Start the voice conversation"}
        >
          <span className="mic-glyph" aria-hidden>
            🎙️
          </span>
          <span className="mic-ring" aria-hidden />
        </button>
        {active && (
          <span className="mic-label">
            {listening ? "Listening…" : v.digitald === "requested" ? "Waiting for identity…" : "In call"}
          </span>
        )}
        {active && (
          <button className="mic-end" type="button" onClick={() => v.send({ type: "stop" })}>
            End conversation
          </button>
        )}
      </div>

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
    </div>
  );
}
