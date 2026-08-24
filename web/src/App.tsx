import { useEffect, useRef, useState } from "react";
import { Header, type AppRole } from "./components/Header";
import { DocumentPanel } from "./components/DocumentPanel";
import { VoicePanel } from "./components/VoicePanel";
import { SummaryPanel } from "./components/SummaryPanel";
import { MortgageChecklist, MortgageProgress } from "./components/MortgageChecklist";
import { PhoneButton } from "./components/PhoneButton";
import { BankWorkspace } from "./components/BankWorkspace";
import { AppointmentPanel } from "./components/AppointmentPanel";
import {
  BankingOverview,
  CardsView,
  CustomerMenu,
  OtherServicesView,
  PersonalInfoView,
  type CustomerService,
} from "./components/CustomerBanking";
import { useEventStream } from "./lib/useEventStream";
import { useVoice } from "./lib/useVoice";
import { cancelSpeech, speak } from "./lib/speech";
import { getCase } from "./lib/api";

function roleFromPath(): AppRole {
  return window.location.pathname.startsWith("/bank") ? "advisor" : "customer";
}

export default function App() {
  const { events, epoch, conn } = useEventStream();
  const v = useVoice();
  const [step, setStep] = useState<number>(1);
  const [role, setRole] = useState<AppRole>(roleFromPath);
  const [customerService, setCustomerService] = useState<CustomerService | null>(null);
  const [mortgagePage, setMortgagePage] = useState<"overview" | "application">("overview");
  const [incomeVerified, setIncomeVerified] = useState(false);
  const [affordabilityComplete, setAffordabilityComplete] = useState(false);
  const [bankReviewComplete, setBankReviewComplete] = useState(false);
  const [appointmentComplete, setAppointmentComplete] = useState(false);
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

  useEffect(() => {
    let active = true;
    getCase()
      .then((caseView) => {
        if (!active) return;
        const verified =
          caseView.document_state === "accepted_automatically" ||
          caseView.document_state === "accepted_after_review";
        setIncomeVerified(verified);
        setAffordabilityComplete(caseView.capacity_result !== null);
        setBankReviewComplete(caseView.advisor_summary !== null);
        setAppointmentComplete(caseView.booked_meeting !== null);
        if (!verified) setStep(1);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [events.length, epoch, mortgagePage, conn]);

  // Speak each new assistant line aloud (neural TTS + browser fallback). Lives at app
  // scope so playback continues smoothly across step transitions.
  useEffect(() => {
    if (v.transcript.length < spokenRef.current) {
      spokenRef.current = 0;
      cancelSpeech();
      return;
    }
    for (let i = spokenRef.current; i < v.transcript.length; i++) {
      if (v.transcript[i].who === "agent" && v.provider !== "foundry") speak(v.transcript[i].text);
    }
    spokenRef.current = v.transcript.length;
  }, [v.transcript]);

  const cardBlocked = events.some(
    (e) => e.event_type === "tool.completed" && e.display.label === "Block card & order replacement",
  );
  useEffect(() => {
    if (cardBlocked && role === "customer") setCustomerService("cards");
  }, [cardBlocked, role]);

  const phoneUpdated = events.some(
    (e) => e.event_type === "tool.completed" && e.display.label === "Update phone number",
  );

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
              {customerService === "profile" && (
                <PersonalInfoView
                  refreshKey={events.length}
                  phoneUpdated={phoneUpdated}
                />
              )}
              {customerService === "cards" && <CardsView refreshKey={events.length} />}
              {customerService === "other" && <OtherServicesView />}
              {customerService === "mortgage" && mortgagePage === "overview" && (
                <MortgageChecklist
                  activeStep={step}
                  incomeVerified={incomeVerified}
                  affordabilityComplete={affordabilityComplete}
                  bankReviewComplete={bankReviewComplete}
                  appointmentComplete={appointmentComplete}
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
                  <MortgageProgress
                    activeStep={step}
                    incomeVerified={incomeVerified}
                    affordabilityComplete={affordabilityComplete}
                    bankReviewComplete={bankReviewComplete}
                    appointmentComplete={appointmentComplete}
                    onOpenStep={setStep}
                  />
                  <div className="mortgage-page-heading">
                    <p className="eyebrow">Mortgage application</p>
                    <h1>
                      {step === 1
                        ? "Income verification"
                        : step === 2
                          ? "Credit & affordability"
                          : step === 3
                            ? "Bank review"
                            : "Appointment"}
                    </h1>
                  </div>
                  {step === 1 && (
                    <DocumentPanel
                      role="customer"
                      refreshKey={events.length}
                      onContinue={() => setStep(2)}
                    />
                  )}
                  {step === 2 && (
                    <VoicePanel
                      v={v}
                      refreshKey={events.length}
                      onContinue={bankReviewComplete ? () => setStep(3) : undefined}
                    />
                  )}
                  {step === 3 && (
                    <SummaryPanel
                      refreshKey={events.length}
                      audience="customer"
                      onContinue={bankReviewComplete ? () => setStep(4) : undefined}
                    />
                  )}
                  {step === 4 && <AppointmentPanel v={v} refreshKey={events.length} />}
                </div>
              )}
            </section>
          </main>
        ) : (
          <BankWorkspace
            events={events}
            refreshKey={events.length}
            incomeVerified={incomeVerified}
            affordabilityComplete={affordabilityComplete}
            bankReviewComplete={bankReviewComplete}
            appointmentComplete={appointmentComplete}
          />
        )}
      </div>
      <PhoneButton voice={v} />
    </div>
  );
}
