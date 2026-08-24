import { useEffect, useState } from "react";
import {
  cancelAppointment,
  getAppointmentAvailability,
  getCase,
  rebookAppointment,
  type AppointmentSlot,
  type DemoCaseView,
} from "../lib/api";

export function AppointmentPanel({
  refreshKey,
  onBookingChange,
}: {
  refreshKey: number;
  onBookingChange: (booked: boolean) => void;
}) {
  const [caseView, setCaseView] = useState<DemoCaseView | null>(null);
  const [slots, setSlots] = useState<AppointmentSlot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [rebooking, setRebooking] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    let active = true;
    getCase()
      .then(async (nextCase) => {
        if (!active) return;
        setCaseView(nextCase);
        if (nextCase.offered_meeting_slots.length > 0) {
          setSlots(nextCase.offered_meeting_slots);
          setError(null);
          return;
        }
        const availability = await getAppointmentAvailability();
        if (!active) return;
        setSlots(availability.slots);
        setError(null);
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Unable to load advisor availability");
        }
      });
    return () => {
      active = false;
    };
  }, [refreshKey]);

  const meeting = caseView?.booked_meeting;
  const visibleSlots = meeting && !slots.some((slot) => slot.slot_id === meeting.slot.slot_id)
    ? [...slots, meeting.slot]
    : slots;
  const firstSlot = visibleSlots[0];
  const weekHeading = firstSlot
    ? `Week of ${new Date(firstSlot.start).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })}`
    : "Available appointments";

  const selectNewSlot = async (slotId: string) => {
    if (!rebooking || updating || slotId === meeting?.slot.slot_id) return;
    setUpdating(true);
    setError(null);
    try {
      const bookedMeeting = await rebookAppointment(slotId);
      setCaseView((current) => current ? { ...current, booked_meeting: bookedMeeting } : current);
      setRebooking(false);
      onBookingChange(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to rebook the appointment");
    } finally {
      setUpdating(false);
    }
  };

  const cancelBooking = async () => {
    if (!meeting || updating) return;
    setUpdating(true);
    setError(null);
    try {
      await cancelAppointment();
      setCaseView((current) => current ? { ...current, booked_meeting: null } : current);
      setRebooking(false);
      onBookingChange(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to cancel the appointment");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="appointment-panel">
      {error && <p className="doc-error" role="alert">{error}</p>}

      <section className="appointment-calendar" aria-label="Available mortgage advisor appointments">
        <div className="appointment-calendar-head">
          <div>
            <p className="eyebrow">Advisor calendar</p>
            <h3>{weekHeading}</h3>
          </div>
          <span>Europe/Stockholm</span>
        </div>
        <div className="appointment-week">
          {visibleSlots.map((slot) => {
            const start = new Date(slot.start);
            const booked = meeting?.slot.slot_id === slot.slot_id;
            const slotBody = (
              <>
                <div className="appointment-date">
                  <span>{start.toLocaleDateString("en-GB", { weekday: "short" })}</span>
                  <strong>{start.getDate()}</strong>
                  <small>{start.toLocaleDateString("en-GB", { month: "short" })}</small>
                </div>
                <div className="appointment-slot">
                  <strong>{start.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</strong>
                  <span>{slot.advisor}</span>
                  <b>{booked ? "✓ Booked" : rebooking ? "Select time" : "Available"}</b>
                </div>
              </>
            );
            return (
              <article key={slot.slot_id} className={`appointment-day ${booked ? "booked" : ""}`}>
                {rebooking && !booked ? (
                  <button
                    type="button"
                    className="appointment-slot-button"
                    onClick={() => void selectNewSlot(slot.slot_id)}
                    disabled={updating}
                  >
                    {slotBody}
                  </button>
                ) : slotBody}
              </article>
            );
          })}
        </div>
      </section>

      <section className="appointment-bookings">
        <div className="appointment-bookings-head">
          <div>
            <p className="eyebrow">Appointments</p>
            <h2>Your bookings</h2>
          </div>
          {meeting && <span className="booking-status">Confirmed</span>}
        </div>
        {meeting ? (
          <div className="appointment-booking-row">
            <span className="appointment-confirmed-check" aria-hidden>✓</span>
            <div className="appointment-booking-details">
              <strong>{new Date(meeting.slot.start).toLocaleString("en-GB", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}</strong>
              <span>{meeting.slot.advisor} · {meeting.booking_reference}</span>
            </div>
            <div className="appointment-actions">
              <button type="button" onClick={() => setRebooking((value) => !value)} disabled={updating}>
                {rebooking ? "Keep booking" : "Rebook"}
              </button>
              <button type="button" className="cancel" onClick={() => void cancelBooking()} disabled={updating}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p className="appointment-empty">
            No appointment booked. Use the Call us button to ask the assistant to book an available time.
          </p>
        )}
      </section>
    </div>
  );
}
