import { useState } from "react";
import { StepNav } from "./components/StepNav";
import { Header } from "./components/Header";
import { UnderTheHood } from "./components/UnderTheHood";
import { DocumentPanel } from "./components/DocumentPanel";
import { VoicePanel } from "./components/VoicePanel";
import { useEventStream } from "./lib/useEventStream";
import { resetDemo } from "./lib/api";

export default function App() {
  const { events, conn } = useEventStream();
  const [step, setStep] = useState<number>(1);

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
          <StepNav active={step} />
          {step === 1 && <DocumentPanel onContinue={() => setStep(2)} />}
          {step === 2 && <VoicePanel />}
        </section>
        <UnderTheHood events={events} />
      </main>
    </div>
  );
}
