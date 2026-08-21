import { useEffect, useRef, useState } from "react";
import { StepNav } from "./components/StepNav";
import { Header } from "./components/Header";
import { UnderTheHood } from "./components/UnderTheHood";
import { DocumentPanel } from "./components/DocumentPanel";
import { VoicePanel } from "./components/VoicePanel";
import { PresenterBar } from "./components/PresenterBar";
import { SummaryPanel } from "./components/SummaryPanel";
import { useEventStream } from "./lib/useEventStream";
import { useVoice } from "./lib/useVoice";
import { cancelSpeech, speak } from "./lib/speech";
import { resetDemo } from "./lib/api";

export default function App() {
  const { events, conn, epoch } = useEventStream();
  const v = useVoice();
  const [step, setStep] = useState<number>(1);
  const lastEpoch = useRef(epoch);
  const spokenRef = useRef(0);

  // Reset-during-call: any epoch bump (presenter reset from anywhere) returns to Screen 1.
  useEffect(() => {
    if (epoch !== lastEpoch.current) {
      lastEpoch.current = epoch;
      setStep(1);
    }
  }, [epoch]);

  // Speak each new assistant line aloud (neural TTS + browser fallback). Lives at app
  // scope so playback continues smoothly across step transitions.
  useEffect(() => {
    if (v.transcript.length < spokenRef.current) {
      spokenRef.current = 0;
      cancelSpeech();
      return;
    }
    for (let i = spokenRef.current; i < v.transcript.length; i++) {
      if (v.transcript[i].who === "agent") speak(v.transcript[i].text);
    }
    spokenRef.current = v.transcript.length;
  }, [v.transcript]);

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
      {/* Recordable area — the live product surface the presenter screen-captures. */}
      <div className="rec-frame">
        <Header conn={conn} onReset={onReset} />
        <main className={`split ${step === 1 ? "solo" : ""}`}>
          <section className="pane stage">
            <p className="pane-title">Customer journey</p>
            <StepNav active={step} onGo={setStep} />
            {step === 1 && <DocumentPanel onContinue={() => setStep(2)} />}
            {step === 2 && <VoicePanel v={v} />}
            {step === 3 && <SummaryPanel refreshKey={events.length} />}
          </section>
          {step !== 1 && <UnderTheHood events={events} />}
        </main>
      </div>
      {/* Presenter controls — outside the recording: scripted customer lines. */}
      {step === 2 && <PresenterBar v={v} />}
    </div>
  );
}
