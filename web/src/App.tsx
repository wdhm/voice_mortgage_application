import { useEffect, useRef, useState } from "react";
import { Header, type AppRole } from "./components/Header";
import { UnderTheHood } from "./components/UnderTheHood";
import { DocumentPanel } from "./components/DocumentPanel";
import { VoicePanel } from "./components/VoicePanel";
import { PresenterBar } from "./components/PresenterBar";
import { SummaryPanel } from "./components/SummaryPanel";
import { MortgageChecklist } from "./components/MortgageChecklist";
import {
  BankingOverview,
  CardsView,
  CustomerMenu,
  OtherServicesView,
  type CustomerService,
} from "./components/CustomerBanking";
import { useEventStream } from "./lib/useEventStream";
import { useVoice } from "./lib/useVoice";
import { cancelSpeech, speak } from "./lib/speech";

function roleFromPath(): AppRole {
  return window.location.pathname.startsWith("/bank") ? "advisor" : "customer";
}

export default function App() {
  const { events, epoch } = useEventStream();
  const v = useVoice();
  const [step, setStep] = useState<number>(1);
  const [role, setRole] = useState<AppRole>(roleFromPath);
  const [customerService, setCustomerService] = useState<CustomerService | null>(null);
  const [mortgagePage, setMortgagePage] = useState<"overview" | "application">("overview");
  const lastEpoch = useRef(epoch);
  const spokenRef = useRef(0);

  useEffect(() => {
    const onPopState = () => setRole(roleFromPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

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

  const selectCustomerService = (service: CustomerService) => {
    setCustomerService(service);
    if (service === "mortgage") setMortgagePage("overview");
  };

  const switchRole = (next: AppRole) => {
    window.history.pushState({}, "", next === "advisor" ? "/bank" : "/");
    setRole(next);
  };

  return (
    <div className="app">
      {/* Recordable area — the live product surface the presenter screen-captures. */}
      <div className="rec-frame">
        <Header role={role} onSwitch={switchRole} />
        {role === "customer" ? (
          <main className="customer-banking">
            <CustomerMenu active={customerService} onSelect={selectCustomerService} />
            <section className="customer-content">
              {customerService === null && <BankingOverview onSelect={selectCustomerService} />}
              {customerService === "cards" && <CardsView refreshKey={events.length} />}
              {customerService === "other" && <OtherServicesView />}
              {customerService === "mortgage" && mortgagePage === "overview" && (
                <MortgageChecklist
                  activeStep={step}
                  onOpenStep={(n) => {
                    setStep(n);
                    setMortgagePage("application");
                  }}
                />
              )}
              {customerService === "mortgage" && mortgagePage === "application" && (
                <div className="mortgage-journey">
                  <button
                    type="button"
                    className="mortgage-back"
                    onClick={() => setMortgagePage("overview")}
                  >
                    ← Application overview
                  </button>
                  <div className="mortgage-page-heading">
                    <p className="eyebrow">Mortgage application</p>
                    <h1>{step === 1 ? "Income verification" : step === 2 ? "Credit & affordability" : "Bank review"}</h1>
                  </div>
                  {step === 1 && (
                    <DocumentPanel role="customer" refreshKey={events.length} />
                  )}
                  {step === 2 && <VoicePanel v={v} />}
                  {step === 3 && <SummaryPanel refreshKey={events.length} />}
                </div>
              )}
            </section>
          </main>
        ) : (
          <main className="split advisor-layout">
            <section className="pane stage advisor-workspace">
              <div>
                <p className="pane-title">Bank representative workspace</p>
                <DocumentPanel role="advisor" refreshKey={events.length} />
              </div>
              <div className="advisor-summary">
                <SummaryPanel refreshKey={events.length} />
              </div>
            </section>
            <UnderTheHood events={events} />
          </main>
        )}
      </div>
      {/* Presenter controls — outside the recording: scripted customer lines. */}
      {role === "customer" && customerService === "mortgage" && mortgagePage === "application" && step === 2 && (
        <PresenterBar v={v} />
      )}
    </div>
  );
}
