import { StepNav } from "./components/StepNav";
import { Header } from "./components/Header";
import { UnderTheHood } from "./components/UnderTheHood";
import { useEventStream } from "./lib/useEventStream";
import { emitEcho, resetDemo } from "./lib/api";

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
          <div className="placeholder">
            <h2>Bank Alfa mortgage journey</h2>
            <p>The income document, voice application, and advisor summary appear here.</p>
            <button
              className="icon-btn"
              style={{ marginTop: 16 }}
              onClick={() => emitEcho("Smoke test event")}
            >
              Emit test event
            </button>
          </div>
        </section>
        <UnderTheHood events={events} />
      </main>
    </div>
  );
}
