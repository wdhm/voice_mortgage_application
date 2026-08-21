import { useCallback, useEffect, useRef, useState } from "react";
import type { VoiceMessage } from "./api";
import { BrowserVoiceAudio } from "./voiceAudio";

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
  transcript: TranscriptLine[];
  consent: ConsentPrompt | null;
  starting: boolean;
  error: string | null;
  start: () => Promise<void>;
  stop: () => void;
  send: (frame: Record<string, unknown>) => void;
}

/**
 * Subscribes to /ws/voice and projects the sanitized voice channel into UI state:
 * running transcript and the latest consent prompt. Governance
 * lives on the server — this hook only reflects it.
 */
export function useVoice(): VoiceStreamState {
  const [conn, setConn] = useState<VoiceConn>("connecting");
  const [provider, setProvider] = useState("");
  const [session, setSession] = useState<"idle" | "active">("idle");
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [consent, setConsent] = useState<ConsentPrompt | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<BrowserVoiceAudio | null>(null);

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
            setStarting(false);
            if (m.state === "idle") {
              void audioRef.current?.stopCapture();
              audioRef.current?.interrupt();
              setTranscript([]);
              setConsent(null);
            }
            break;
          case "agent_transcript":
            setTranscript((t) => [...t, { who: "agent", text: m.text }]);
            break;
          case "user_transcript":
            setTranscript((t) => [...t, { who: "customer", text: m.text }]);
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
          case "audio":
            audioRef.current?.play(m.pcm);
            break;
          case "barge_in":
          case "agent_interrupted":
            audioRef.current?.interrupt();
            break;
          case "error":
            setStarting(false);
            setError(m.message);
            void audioRef.current?.stopCapture();
            break;
        }
      };
      ws.onclose = () => {
        if (closed) return;
        setStarting(false);
        setConn("reconnecting");
        void audioRef.current?.stopCapture();
        retry = setTimeout(connect, 1000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      wsRef.current?.close();
      void audioRef.current?.close();
      setConn("closed");
    };
  }, []);

  const send = useCallback((frame: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(frame));
  }, []);

  const start = useCallback(async () => {
    if (starting || session === "active") return;
    setError(null);
    setStarting(true);
    audioRef.current ??= new BrowserVoiceAudio();
    try {
      await audioRef.current.startCapture(send);
      send({ type: "start" });
    } catch (caught) {
      setStarting(false);
      setError(caught instanceof Error ? caught.message : "Unable to start microphone access.");
    }
  }, [send, session, starting]);

  const stop = useCallback(() => {
    setStarting(false);
    void audioRef.current?.stopCapture();
    audioRef.current?.interrupt();
    send({ type: "stop" });
  }, [send]);

  return {
    conn,
    provider,
    session,
    transcript,
    consent,
    starting,
    error,
    start,
    stop,
    send,
  };
}
