import { useEffect, useState } from "react";
import { getCase, type DemoCaseView } from "../lib/api";
import type { VoiceStreamState } from "../lib/useVoice";
import { VoicePanel } from "./VoicePanel";

export function AppointmentPanel({
  v,
  refreshKey,
}: {
  v: VoiceStreamState;
  refreshKey: number;
}) {
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);

  useEffect(() => {
    getCase().then(setCaseView).catch(() => {});
  }, [refreshKey, v.transcript.length]);

  const meeting = caseView?.booked_meeting;
  if (!meeting) {
    return (
      <div className="appointment-panel">
        <section className="appointment-intro">
          <span className="appointment-icon" aria-hidden>□</span>
          <div>
            <h2>Arrange your advisor appointment</h2>
            <p>
              Continue the conversation to choose a suitable time with a mortgage advisor.
            </p>
          </div>
        </section>
        <VoicePanel
          v={v}
          refreshKey={refreshKey}
          title="Appointment scheduling"
          description="Tell the assistant when you are available. Your booking appears here as soon as it is confirmed."
          showAssessment={false}
        />
      </div>
    );
  }

  return (
    <section className="appointment-confirmed">
      <span className="appointment-confirmed-check" aria-hidden>✓</span>
      <div>
        <p className="eyebrow">Appointment confirmed</p>
        <h2>{new Date(meeting.slot.start).toLocaleString("en-GB", {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}</h2>
        <p>{meeting.slot.advisor} · {meeting.purpose}</p>
        <dl>
          <div><dt>Booking reference</dt><dd>{meeting.booking_reference}</dd></div>
          <div><dt>Status</dt><dd>Confirmed</dd></div>
        </dl>
        <small>
          Your advisor will review the complete application and remains responsible for the final decision.
        </small>
      </div>
    </section>
  );
}
