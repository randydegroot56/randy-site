'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession, signIn } from 'next-auth/react';
import { AnimatePresence } from 'framer-motion';
import AnimateIn from '../../components/AnimateIn';
import CalendarHeader from '../../components/Calendar/CalendarHeader';
import CalendarGrid from '../../components/Calendar/CalendarGrid';
import WeekView from '../../components/Calendar/WeekView';
import EventDetailPanel from '../../components/Calendar/EventDetailPanel';
import EventForm from '../../components/Calendar/EventForm';

function getWeekStart(date) {
  const d = new Date(date);
  d.setDate(d.getDate() - (d.getDay() + 6) % 7);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getMonthRange(date) {
  const start = new Date(date.getFullYear(), date.getMonth(), 1);
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 1);
  return { start, end };
}

function getWeekRange(date) {
  const start = getWeekStart(date);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return { start, end };
}

export default function CalendarPage() {
  const { data: session, status } = useSession();

  const [view, setView] = useState('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [formEvent, setFormEvent] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    if (status === 'unauthenticated') {
      signIn('google');
    }
  }, [status]);

  const fetchEvents = useCallback(async () => {
    if (!session) return;
    setLoadingEvents(true);
    setFetchError(null);
    try {
      const { start, end } = view === 'month'
        ? getMonthRange(currentDate)
        : getWeekRange(currentDate);
      const res = await fetch(
        `/api/calendar/events?start=${start.toISOString()}&end=${end.toISOString()}`
      );
      if (!res.ok) throw new Error('Ophalen mislukt');
      const data = await res.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch (err) {
      setFetchError(err.message);
    } finally {
      setLoadingEvents(false);
    }
  }, [session, view, currentDate]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handlePrev = () => {
    const d = new Date(currentDate);
    if (view === 'month') d.setMonth(d.getMonth() - 1);
    else d.setDate(d.getDate() - 7);
    setCurrentDate(d);
  };

  const handleNext = () => {
    const d = new Date(currentDate);
    if (view === 'month') d.setMonth(d.getMonth() + 1);
    else d.setDate(d.getDate() + 7);
    setCurrentDate(d);
  };

  const handleSave = async ({ id, title, startDateTime, endDateTime, description, location }) => {
    setFormLoading(true);
    try {
      const body = { title, startDateTime, endDateTime, description, location };
      const res = id
        ? await fetch(`/api/calendar/events/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })
        : await fetch('/api/calendar/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
      if (!res.ok) throw new Error('Opslaan mislukt');
      setFormOpen(false);
      setFormEvent(null);
      setSelectedEvent(null);
      await fetchEvents();
    } catch (err) {
      alert(err.message);
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`/api/calendar/events/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Verwijderen mislukt');
      setSelectedEvent(null);
      await fetchEvents();
    } catch (err) {
      alert(err.message);
    }
  };

  const openCreateForm = () => {
    setFormEvent({});
    setFormOpen(true);
    setSelectedEvent(null);
  };

  const openEditForm = (event) => {
    setFormEvent(event);
    setFormOpen(true);
    setSelectedEvent(null);
  };

  if (status === 'loading') {
    return (
      <section style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
          LADEN...
        </span>
      </section>
    );
  }

  if (!session) return null;

  return (
    <section style={{ minHeight: '100vh', padding: 'var(--space-20) var(--space-6)' }}>
      <div style={{ width: '100%', maxWidth: '1100px', margin: '0 auto' }}>

        <AnimateIn delay={0.05}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-6)' }}>
            <span style={{
              display: 'inline-block', width: 6, height: 6,
              borderRadius: '50%', background: 'var(--accent-primary)',
              boxShadow: '0 0 8px rgba(232,185,49,0.7)',
            }} />
            <span style={{
              fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
              letterSpacing: '0.18em', textTransform: 'uppercase',
              color: 'var(--accent-secondary)',
            }}>
              RDG.DEV // KALENDER
            </span>
          </div>

          <div style={{ marginBottom: 'var(--space-10)' }}>
            <div style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)',
              fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em',
              color: 'var(--text-primary)',
            }}>
              AGENDA
            </div>
            <div style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)',
              fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em',
              color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)',
            }}>
              DASHBOARD.
            </div>
          </div>
        </AnimateIn>

        <AnimateIn delay={0.1}>
          <CalendarHeader
            view={view}
            onViewChange={setView}
            currentDate={currentDate}
            onPrev={handlePrev}
            onNext={handleNext}
            onNewEvent={openCreateForm}
          />

          {fetchError && (
            <div style={{
              padding: 'var(--space-4)',
              border: '1px solid rgba(239,68,68,0.3)',
              backgroundColor: 'rgba(239,68,68,0.05)',
              marginBottom: 'var(--space-4)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-sm)', color: 'rgba(239,68,68,0.9)' }}>
                {fetchError}
              </span>
              <button
                onClick={fetchEvents}
                style={{
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', fontWeight: 700,
                  letterSpacing: '0.1em', color: 'var(--accent-secondary)',
                  background: 'none', border: 'none', cursor: 'pointer',
                }}
              >
                OPNIEUW
              </button>
            </div>
          )}

          {loadingEvents && (
            <div style={{
              textAlign: 'center', padding: 'var(--space-8)',
              fontFamily: 'monospace', fontSize: 'var(--text-xs)',
              color: 'var(--text-muted)', letterSpacing: '0.12em',
            }}>
              EVENTS LADEN...
            </div>
          )}

          {!loadingEvents && view === 'month' && (
            <CalendarGrid
              currentDate={currentDate}
              events={events}
              onEventClick={setSelectedEvent}
            />
          )}

          {!loadingEvents && view === 'week' && (
            <WeekView
              currentDate={currentDate}
              events={events}
              onEventClick={setSelectedEvent}
            />
          )}
        </AnimateIn>
      </div>

      <AnimatePresence>
        {selectedEvent && (
          <EventDetailPanel
            key="detail-panel"
            event={selectedEvent}
            onClose={() => setSelectedEvent(null)}
            onEdit={openEditForm}
            onDelete={handleDelete}
          />
        )}
      </AnimatePresence>

      {formOpen && (
        <EventForm
          event={formEvent && formEvent.id ? formEvent : null}
          onSave={handleSave}
          onClose={() => { setFormOpen(false); setFormEvent(null); }}
          loading={formLoading}
        />
      )}
    </section>
  );
}
