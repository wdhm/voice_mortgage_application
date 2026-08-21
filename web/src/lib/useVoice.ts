import { useCallback, useEffect, useRef, useState } from "react";
import type { VoiceMessage } from "./api";

export type VoiceConn = "connecting" | "ready" | "reconnecting" | "closed";

export interface TranscriptLine {
  who: "agent" | "customer";
  text: string;
}

export interface ConsentPrompt {
  action: string;
  scope: string | null;
  consent_id: string;
  status: "requested" | "granted" | "denied" | "consumed" | "expired";
}

export interface VoiceStreamState {
  conn: VoiceConn;
  provider: string;
  session: "idle" | "active";
  digitald: "none" | "requested" | "approved";
  transcript: TranscriptLine[];
  consent: ConsentPrompt | null;
  send: (frame: Record<string, unknown>) => void;
}

/**
 * Subscribes to /ws/voice and projects the sanitized voice channel into UI state:
 * running transcript, DigitalD state, and the latest consent prompt. Governance
 * lives on the server — this hook only reflects it.
 */
export function useVoice(): VoiceStreamState {
  const [conn, setConn] = useState<VoiceConn>("connecting");
  const [provider, setProvider] = useState("");
  const [session, setSession] = useState<"idle" | "active">("idle");
  const [digitald, setDigitald] = useState<"none" | "requested" | "approved">("none");
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [consent, setConsent] = useState<ConsentPrompt | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/ws/voice`);
      wsRef.current = ws;

      ws.onopen = () => setConn("ready");
      ws.onmessage = (ev) => {
        const m: VoiceMessage = JSON.parse(ev.data);
        switch (m.type) {
          case "hello":
            setProvider(m.provider);
            break;
          case "session":
            setSession(m.state);
            setProvider(m.provider);
            if (m.state === "idle") {
              setTranscript([]);
              setConsent(null);
              setDigitald("none");
            }
            break;
          case "agent_transcript":
            setTranscript((t) => [...t, { who: "agent", text: m.text }]);
            break;
          case "user_transcript":
            setTranscript((t) => [...t, { who: "customer", text: m.text }]);
            break;
          case "digitald":
            setDigitald(m.state);
            break;
          case "consent":
            if (m.status === "requested") {
              setConsent({ action: m.action, scope: m.scope, consent_id: m.consent_id, status: m.status });
            } else {
              setConsent((c) =>
                c && c.consent_id === m.consent_id ? { ...c, status: m.status } : c,
              );
            }
            break;
        }
      };
      ws.onclose = () => {
        if (closed) return;
        setConn("reconnecting");
        retry = setTimeout(connect, 1000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      wsRef.current?.close();
      setConn("closed");
    };
  }, []);

  const send = useCallback((frame: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(frame));
  }, []);

  return { conn, provider, session, digitald, transcript, consent, send };
}
