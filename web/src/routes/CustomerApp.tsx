import { FormEvent, useEffect, useRef, useState } from "react";
import {
  CalendarCheck,
  Check,
  FileText,
  LockKeyhole,
  MessageCircle,
  Mic,
  Send,
  ShieldCheck,
  Upload,
  Wifi,
} from "lucide-react";
import { api, jsonRequest, websocketUrl } from "../api";
import { createPayslipSample, type PayslipSampleQuality } from "../documents/samplePayslip";
import type { CustomerCase } from "../types";
import { useVoiceLive } from "../voice/useVoiceLive";

const emptyCase: CustomerCase = {
  customer_name: "Emma Lindberg",
  identity_status: "not_identified",
  document: { name: null, status: "not_uploaded" },
  transcript: [],
  meeting: null,
  card: null,
};

export function CustomerApp() {
  const [caseState, setCaseState] = useState(emptyCase);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    setCaseState(await api<CustomerCase>("/api/customer/case"));
  }

  const voice = useVoiceLive(() => void refresh());

  useEffect(() => {
    void refresh();
    const socket = new WebSocket(websocketUrl("customer"));
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = () => void refresh();
    return () => socket.close();
  }, []);

  async function upload(file: File | undefined) {
    if (!file) {
      setError("Choose a payslip or use one of the fictional samples");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    setBusy(true);
    setError("");
    try {
      setCaseState(await api<CustomerCase>("/api/customer/documents", { method: "POST", body: form }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function uploadSample(quality: PayslipSampleQuality) {
    await upload(await createPayslipSample(quality));
  }

  async function digitalD(approved: boolean) {
    setCaseState(await api<CustomerCase>("/api/customer/digitald", jsonRequest("POST", { approved })));
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    const text = message;
    setMessage("");
    setBusy(true);
    try {
      const result = await api<{ case: CustomerCase }>("/api/customer/messages", jsonRequest("POST", { text }));
      setCaseState(result.case);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Message failed");
    } finally {
      setBusy(false);
    }
  }

  const documentAccepted = caseState.document.status.startsWith("accepted");
  const documentPending = caseState.document.status === "review_required";
  const activeStep = !documentAccepted ? 1 : caseState.meeting ? 3 : 2;

  return (
    <div className="customer-shell">
      <header className="customer-header">
        <div className="brand"><span className="brand-mark">A</span><strong>Bank Alfa</strong></div>
        <div className="session-state"><Wifi size={16} />{connected ? "Secure session" : "Connecting"}</div>
      </header>

      <main className="customer-main">
        <p className="eyebrow">Your mortgage application</p>
        <h1>Welcome, Emma</h1>
        <ol className="progress" aria-label="Application progress">
          {["Income document", "Voice application", "Appointment"].map((label, index) => (
            <li className={activeStep >= index + 1 ? "active" : ""} key={label}>
              <span>{activeStep > index + 1 ? <Check size={16} /> : index + 1}</span>{label}
            </li>
          ))}
        </ol>

        {error && <div className="alert danger" role="alert">{error}</div>}

        {!documentAccepted ? (
          <section className="customer-work" aria-labelledby="income-title">
            <div>
              <p className="section-kicker">Step 1</p>
              <h2 id="income-title">Add your latest payslip</h2>
              <p className="supporting">PDF, PNG or JPEG, up to 10 MB.</p>
            </div>
            <div className="upload-zone">
              <FileText size={42} />
              <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg" aria-label="Choose payslip" />
              <button className="primary" onClick={() => void upload(fileRef.current?.files?.[0])} disabled={busy}>
                <Upload size={18} />{busy ? "Reviewing..." : "Upload payslip"}
              </button>
              <div className="sample-actions" aria-label="Demo samples">
                <button onClick={() => void uploadSample("high")} disabled={busy}>Clear fictional sample</button>
                <button onClick={() => void uploadSample("low")} disabled={busy}>Unclear fictional sample</button>
              </div>
            </div>
            {documentPending && <div className="alert review">Your document needs a manual review. You can replace it while we check the details.</div>}
          </section>
        ) : (
          <section className="conversation-layout" aria-labelledby="conversation-title">
            <div className="conversation-stage">
              <div className="verified-strip"><ShieldCheck size={20} />Your income document has been received</div>
              <p className="section-kicker">Step 2</p>
              <h2 id="conversation-title">Talk with Bank Alfa</h2>
              {caseState.identity_status !== "identified" ? (
                <div className="identity-panel" role="dialog" aria-modal="true" aria-labelledby="digitald-title">
                  <LockKeyhole size={28} />
                  <div><p className="section-kicker">Demo identity check</p><h3 id="digitald-title">DigitalD</h3><p>Identify Emma Lindberg for this Bank Alfa session.</p></div>
                  <div className="button-row">
                    <button className="secondary" onClick={() => void digitalD(false)}>Decline</button>
                    <button className="primary" onClick={() => void digitalD(true)}><Check size={18} />Approve</button>
                  </div>
                </div>
              ) : (
                <>
                  <button
                    className={`mic-control ${voice.state}`}
                    type="button"
                    onClick={() => voice.state === "idle" || voice.state === "error" ? void voice.start() : voice.stop()}
                    aria-pressed={voice.state !== "idle" && voice.state !== "error"}
                  >
                    <Mic size={30} />
                    <span>{voice.state === "idle" ? "Start voice" : voice.state === "error" ? "Try again" : voice.state}</span>
                  </button>
                  {voice.error && <div className="alert danger" role="alert">{voice.error}</div>}
                  {voice.partialTranscript && <p className="live-transcript" aria-live="polite">{voice.partialTranscript}</p>}
                  <div className="transcript" aria-live="polite">
                    {caseState.transcript.map((turn, index) => (
                      <div className={`turn ${turn.speaker}`} key={`${turn.speaker}-${index}`}>
                        <strong>{turn.speaker === "customer" ? "Emma" : "Bank Alfa"}</strong><p>{turn.text}</p>
                      </div>
                    ))}
                  </div>
                  <form className="message-box" onSubmit={sendMessage}>
                    <MessageCircle size={19} />
                    <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Type a message" aria-label="Message Bank Alfa" />
                    <button type="submit" title="Send message" aria-label="Send message" disabled={busy}><Send size={19} /></button>
                  </form>
                </>
              )}
            </div>
            <aside className="customer-confirmations">
              <h3>Confirmations</h3>
              {caseState.meeting ? <div className="confirmation"><CalendarCheck /><div><strong>Advisor meeting</strong><span>21 September 2026 · 15:00</span></div></div> : <p>No appointment booked yet.</p>}
              {caseState.card ? <div className="confirmation"><ShieldCheck /><div><strong>{caseState.card.card_type} · {caseState.card.last_four}</strong><span>Blocked · replacement ordered</span></div></div> : null}
            </aside>
          </section>
        )}
      </main>
    </div>
  );
}