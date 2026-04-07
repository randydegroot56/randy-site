'use client';

import EventBlock from './EventBlock';

const HOUR_HEIGHT = 56; // px per hour
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const DAY_LABELS = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'];

function getWeekStart(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - (day + 6) % 7);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getWeekDays(date) {
  const monday = getWeekStart(date);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function getEventsForDay(events, dayDate) {
  return events.filter(event => {
    if (!event.start?.dateTime) return false;
    const eventDate = new Date(event.start.dateTime);
    return eventDate.toDateString() === dayDate.toDateString();
  });
}

function getEventStyle(event) {
  const start = new Date(event.start.dateTime);
  const end = new Date(event.end.dateTime);
  const startMinutes = start.getHours() * 60 + start.getMinutes();
  const durationMinutes = Math.max((end - start) / 60000, 30);
  return {
    position: 'absolute',
    top: (startMinutes / 60) * HOUR_HEIGHT + 'px',
    height: (durationMinutes / 60) * HOUR_HEIGHT + 'px',
    left: '2px',
    right: '2px',
    zIndex: 1,
  };
}

function getCurrentTimeTop() {
  const now = new Date();
  return ((now.getHours() * 60 + now.getMinutes()) / 60) * HOUR_HEIGHT;
}

export default function WeekView({ currentDate, events, onEventClick }) {
  const weekDays = getWeekDays(currentDate);
  const today = new Date();
  const isToday = (d) => d.toDateString() === today.toDateString();
  const timeTop = getCurrentTimeTop();

  return (
    <div style={{ display: 'flex', overflowX: 'auto' }}>
      {/* Time labels column */}
      <div style={{ width: '48px', flexShrink: 0 }}>
        <div style={{ height: '48px' }} />
        {HOURS.map(h => (
          <div
            key={h}
            style={{
              height: HOUR_HEIGHT + 'px',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'flex-end',
              paddingRight: 'var(--space-2)',
              paddingTop: '2px',
            }}
          >
            <span style={{
              fontFamily: 'monospace',
              fontSize: '10px',
              color: 'var(--text-muted)',
              letterSpacing: '0.04em',
            }}>
              {h.toString().padStart(2, '0')}:00
            </span>
          </div>
        ))}
      </div>

      {/* Day columns */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', minWidth: 0 }}>
        {weekDays.map((day, i) => {
          const dayEvents = getEventsForDay(events, day);
          const isCurrentDay = isToday(day);

          return (
            <div key={i} style={{ borderLeft: '1px solid var(--border-subtle)' }}>
              {/* Day header */}
              <div style={{
                height: '48px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                borderBottom: '1px solid var(--border-subtle)',
                backgroundColor: isCurrentDay ? 'rgba(232,185,49,0.05)' : 'transparent',
              }}>
                <span style={{
                  fontFamily: 'monospace',
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '0.1em',
                  color: isCurrentDay ? 'var(--accent-primary)' : 'var(--text-muted)',
                  textTransform: 'uppercase',
                }}>
                  {DAY_LABELS[i]}
                </span>
                <span style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: isCurrentDay ? 700 : 400,
                  color: isCurrentDay ? 'var(--accent-primary)' : 'var(--text-secondary)',
                }}>
                  {day.getDate()}
                </span>
              </div>

              {/* Time grid */}
              <div style={{ position: 'relative', height: HOUR_HEIGHT * 24 + 'px' }}>
                {HOURS.map(h => (
                  <div key={h} style={{
                    position: 'absolute',
                    top: h * HOUR_HEIGHT + 'px',
                    left: 0, right: 0,
                    height: '1px',
                    backgroundColor: 'var(--border-subtle)',
                  }} />
                ))}

                {isCurrentDay && (
                  <div style={{
                    position: 'absolute',
                    top: timeTop + 'px',
                    left: 0, right: 0,
                    height: '2px',
                    backgroundColor: 'var(--accent-primary)',
                    zIndex: 2,
                    boxShadow: '0 0 6px rgba(232,185,49,0.5)',
                  }} />
                )}

                {dayEvents.map(event => (
                  <div key={event.id} style={getEventStyle(event)}>
                    <EventBlock event={event} onClick={onEventClick} compact={false} />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
