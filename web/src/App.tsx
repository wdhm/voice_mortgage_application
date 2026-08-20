import { useEffect, useRef, useState } from "react";
import { StepNav } from "./components/StepNav";
import { Header } from "./components/Header";
import { UnderTheHood } from "./components/UnderTheHood";
import { DocumentPanel } from "./components/DocumentPanel";
import { VoicePanel } from "./components/VoicePanel";
import { SummaryPanel } from "./components/SummaryPanel";
import { useEventStream } from "./lib/useEventStream";
import { resetDemo } from "./lib/api";

export default function App() {
  const { events, conn, epoch } = useEventStream();
  const [step, setStep] = useState<number>(1);
  const lastEpoch = useRef(epoch);

  // Reset-during-call: any epoch bump (presenter reset from anywhere) returns to Screen 1.
  useEffect(() => {
    if (epoch !== lastEpoch.current) {
      lastEpoch.current = epoch;
      setStep(1);
    }
  }, [epoch]);

  // Auto-advance to the advisor summary once the handoff has been written.
  const summaryReady = events.some(
    (e) => e.event_type === "tool.completed" && e.display.label === "Write advisor summary",
  );
  useEffect(() => {
    if (summaryReady && step === 2) setStep(3);
  }, [summaryReady, step]);

  const onReset = async () => {
    await resetDemo();
    setStep(1);
  };

  return (
    <div className="app">
      <Header conn={conn} onReset={onReset} />
      <main className="split">
        <section className="pane journey">
          <p className="pane-title">Customer journey</p>
          <StepNav active={step} onGo={setStep} />
          {step === 1 && <DocumentPanel onContinue={() => setStep(2)} />}
          {step === 2 && <VoicePanel />}
          {step === 3 && <SummaryPanel refreshKey={events.length} />}
        </section>
        <UnderTheHood events={events} />
      </main>
    </div>
  );
}
