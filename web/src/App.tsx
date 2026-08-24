import { useEffect, useRef, useState } from "react";
import { Header, type AppRole } from "./components/Header";
import { DocumentPanel } from "./components/DocumentPanel";
import { VoicePanel } from "./components/VoicePanel";
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
  const [step, setStep] = useState<number>(2);
  const [role, setRole] = useState<AppRole>(roleFromPath);
  const [customerService, setCustomerService] = useState<CustomerService | null>(null);
  const [mortgagePage, setMortgagePage] = useState<"overview" | "application">("overview");
  const [incomeVerified, setIncomeVerified] = useState(false);
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
      setStep(2);
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
        setAppointmentComplete(caseView.booked_meeting !== null);
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
                    appointmentComplete={appointmentComplete}
                    onOpenStep={setStep}
                  />
                  <div className="mortgage-page-heading">
                    <p className="eyebrow">Mortgage application</p>
                    <h1>
                      {step === 1
                        ? "Credit check"
                        : step === 2
                          ? "Income verification"
                          : "Appointment"}
                    </h1>
                  </div>
                  {step === 2 && (
                    <>
                      <DocumentPanel
                        role="customer"
                        refreshKey={events.length}
                        onContinue={() => setStep(3)}
                      />
                      {v.session === "active" && (
                        <VoicePanel
                          v={v}
                          refreshKey={events.length}
                          title="Income verification support"
                          description="Ask us about your payslip or get help uploading a clearer copy."
                          showAssessment={false}
                        />
                      )}
                    </>
                  )}
                  {step === 3 && (
                    <AppointmentPanel
                      refreshKey={events.length}
                      onBookingChange={setAppointmentComplete}
                    />
                  )}
                </div>
              )}
            </section>
          </main>
        ) : (
          <BankWorkspace refreshKey={events.length} />
        )}
      </div>
      <PhoneButton voice={v} />
    </div>
  );
}
