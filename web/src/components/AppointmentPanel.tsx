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
  const calendarDate = firstSlot ? new Date(firstSlot.start) : new Date();
  const calendarYear = calendarDate.getFullYear();
  const calendarMonth = calendarDate.getMonth();
  const monthHeading = calendarDate.toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });
  const daysInMonth = new Date(calendarYear, calendarMonth + 1, 0).getDate();
  const firstDayOfWeek = new Date(calendarYear, calendarMonth, 1).getDay();
  const leadingWeekdays = firstDayOfWeek === 0 || firstDayOfWeek === 6 ? 0 : firstDayOfWeek - 1;
  const calendarDays: Array<number | null> = Array.from({ length: leadingWeekdays }, () => null);
  for (let day = 1; day <= daysInMonth; day++) {
    const weekday = new Date(calendarYear, calendarMonth, day).getDay();
    if (weekday !== 0 && weekday !== 6) calendarDays.push(day);
  }
  while (calendarDays.length % 5 !== 0) calendarDays.push(null);
  const slotsByDay = visibleSlots.reduce<Map<number, AppointmentSlot[]>>((grouped, slot) => {
    const start = new Date(slot.start);
    if (start.getFullYear() === calendarYear && start.getMonth() === calendarMonth) {
      grouped.set(start.getDate(), [...(grouped.get(start.getDate()) ?? []), slot]);
    }
    return grouped;
  }, new Map());

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
            <h3>{monthHeading}</h3>
          </div>
          <span>Europe/Stockholm</span>
        </div>
        <div className="appointment-month-weekdays" aria-hidden>
          {["Mon", "Tue", "Wed", "Thu", "Fri"].map((weekday) => (
            <span key={weekday}>{weekday}</span>
          ))}
        </div>
        <div className="appointment-month-grid">
          {calendarDays.map((day, index) => {
            const daySlots = day === null ? [] : slotsByDay.get(day) ?? [];
            return (
              <div
                key={`${day ?? "blank"}-${index}`}
                className={`appointment-month-day ${day === null ? "outside" : ""} ${daySlots.length ? "has-slots" : ""}`}
              >
                {day !== null && <span className="appointment-day-number">{day}</span>}
                {daySlots.length > 0 && (
                  <>
                    <div className="appointment-time-list">
                      {daySlots.map((slot) => {
                        const booked = meeting?.slot.slot_id === slot.slot_id;
                        const time = new Date(slot.start).toLocaleTimeString("en-GB", {
                          hour: "2-digit",
                          minute: "2-digit",
                        });
                        return rebooking && !booked ? (
                          <button
                            key={slot.slot_id}
                            type="button"
                            className="appointment-time-chip"
                            onClick={() => void selectNewSlot(slot.slot_id)}
                            disabled={updating}
                          >
                            {time}
                          </button>
                        ) : (
                          <span
                            key={slot.slot_id}
                            className={`appointment-time-chip ${booked ? "booked" : ""}`}
                          >
                            {booked ? `✓ ${time}` : time}
                          </span>
                        );
                      })}
                    </div>
                    <small className="appointment-availability-label">Available</small>
                  </>
                )}
              </div>
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
