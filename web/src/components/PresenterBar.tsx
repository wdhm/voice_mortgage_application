import { useRef } from "react";
import type { VoiceStreamState } from "../lib/useVoice";

// Canonical customer utterances for the pre-recorded demo. These are the presenter's
// script — kept OUTSIDE the recordable frame so the captured area looks live. Clicking
// sends the real transcript to the server, which classifies consent and drives tools.
const BEATS = [
  "I want a mortgage pre-approval for a house in Täby, around seven million kronor.",
  "Yes, you can run the credit check.",
  "I have one million seven hundred and fifty thousand kronor deposit.",
  "I'm away for three weeks. Do you have anything after that?",
  "Monday the 21st of September at 15:00 works.",
  "One more thing — my card was stolen.",
  "Yes, block it and order a replacement.",
];

export function PresenterBar({ v }: { v: VoiceStreamState }) {
  const textRef = useRef<HTMLInputElement | null>(null);
  const ready = v.session === "active";

  const sendText = (text: string) => {
    const t = text.trim();
    if (!t) return;
    v.send({ type: "text", text: t });
  };

  return (
    <aside className="presenter-bar" aria-label="Presenter controls, not part of the recording">
      <div className="presenter-tag">
        <span className="pt-dot" /> Presenter · not part of the recording
      </div>
      <div className="presenter-body">
        <div className="beats">
          {BEATS.map((b, i) => (
            <button
              key={i}
              className="beat"
              disabled={!ready}
              onClick={() => sendText(b)}
              title={b}
            >
              {b}
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
          <input ref={textRef} placeholder="Type what Emma says…" disabled={!ready} />
          <button className="icon-btn" type="submit" disabled={!ready}>
            Send
          </button>
        </form>
      </div>
      {!ready && (
        <p className="presenter-hint">
          Start the conversation and approve identity in the recording area, then click Emma's lines.
        </p>
      )}
    </aside>
  );
}
