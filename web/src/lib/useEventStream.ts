import { useEffect, useRef, useState } from "react";
import type { TimelineEvent } from "./api";

export type ConnState = "connecting" | "ready" | "reconnecting" | "failed";

interface WsMessage {
  kind: "event" | "ready";
  data?: TimelineEvent;
  epoch?: number;
}

/**
 * Subscribes to the application WebSocket, keeps the sanitized timeline in sync,
 * and drops events from a superseded epoch (post-reset) client-side as a guard.
 */
export function useEventStream() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [conn, setConn] = useState<ConnState>("connecting");
  const [epoch, setEpoch] = useState<number>(0);
  const epochRef = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/ws/events`);

      ws.onopen = () => setConn("ready");
      ws.onmessage = (ev) => {
        const msg: WsMessage = JSON.parse(ev.data);
        if (msg.kind === "ready" && typeof msg.epoch === "number") {
          epochRef.current = msg.epoch;
          setEpoch(msg.epoch);
          return;
        }
        if (msg.kind === "event" && msg.data) {
          const e = msg.data;
          if (e.epoch < epochRef.current) return; // stale, pre-reset
          if (e.epoch > epochRef.current) {
            // A reset happened: adopt the new epoch and clear the timeline.
            epochRef.current = e.epoch;
            setEpoch(e.epoch);
            setEvents([e]);
            return;
          }
          setEvents((prev) => [...prev, e]);
        }
      };
      ws.onclose = () => {
        if (closed) return;
        setConn("reconnecting");
        retry = setTimeout(connect, 1000);
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, []);

  return { events, conn, epoch };
}
