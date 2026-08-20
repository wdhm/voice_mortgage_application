import { StepNav } from "./components/StepNav";
import { Header } from "./components/Header";
import { UnderTheHood } from "./components/UnderTheHood";
import { DocumentPanel } from "./components/DocumentPanel";
import { useEventStream } from "./lib/useEventStream";
import { resetDemo } from "./lib/api";

export default function App() {
  const { events, conn } = useEventStream();

  const onReset = async () => {
    await resetDemo();
  };

  return (
    <div className="app">
      <Header conn={conn} onReset={onReset} />
      <main className="split">
        <section className="pane journey">
          <p className="pane-title">Customer journey</p>
          <StepNav active={1} />
          <DocumentPanel onContinue={() => { /* M4: advance to voice step */ }} />
        </section>
        <UnderTheHood events={events} />
      </main>
    </div>
  );
}
