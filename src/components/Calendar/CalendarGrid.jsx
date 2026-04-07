'use client';

import EventBlock from './EventBlock';

const DAY_LABELS = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'];

function getMonthCells(year, month) {
  const firstWeekday = new Date(year, month, 1).getDay(); // 0 = Sun
  const paddingStart = (firstWeekday + 6) % 7; // Convert to Mon = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < paddingStart; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

function getEventsForDay(events, year, month, day) {
  return events.filter(event => {
    const d = new Date(event.start?.dateTime || event.start?.date);
    return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
  });
}

export default function CalendarGrid({ currentDate, events, onEventClick }) {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const today = new Date();
  const isToday = (day) =>
    day === today.getDate() && month === today.getMonth() && year === today.getFullYear();

  const cells = getMonthCells(year, month);

  return (
    <div>
      {/* Day headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        marginBottom: 'var(--space-2)',
      }}>
        {DAY_LABELS.map(d => (
          <div key={d} style={{
            fontFamily: 'monospace',
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            textAlign: 'center',
            padding: 'var(--space-2) 0',
          }}>
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        border: '1px solid var(--border-subtle)',
      }}>
        {cells.map((day, i) => {
          const dayEvents = day ? getEventsForDay(events, year, month, day) : [];
          const visibleEvents = dayEvents.slice(0, 3);
          const overflow = dayEvents.length - 3;

          return (
            <div
              key={i}
              style={{
                minHeight: '100px',
                padding: 'var(--space-2)',
                borderRight: (i + 1) % 7 !== 0 ? '1px solid var(--border-subtle)' : 'none',
                borderBottom: i < cells.length - 7 ? '1px solid var(--border-subtle)' : 'none',
                backgroundColor: day ? 'transparent' : 'rgba(0,0,0,0.02)',
                outline: isToday(day) ? '1px solid var(--accent-primary)' : 'none',
                outlineOffset: '-1px',
              }}
            >
              {day && (
                <>
                  <span style={{
                    display: 'block',
                    fontFamily: 'var(--font-heading)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: isToday(day) ? 700 : 400,
                    color: isToday(day) ? 'var(--accent-primary)' : 'var(--text-muted)',
                    marginBottom: 'var(--space-1)',
                    lineHeight: 1,
                  }}>
                    {day}
                  </span>
                  {visibleEvents.map(event => (
                    <EventBlock
                      key={event.id}
                      event={event}
                      onClick={onEventClick}
                      compact
                    />
                  ))}
                  {overflow > 0 && (
                    <span style={{
                      fontFamily: 'monospace',
                      fontSize: '10px',
                      color: 'var(--accent-secondary)',
                      letterSpacing: '0.04em',
                    }}>
                      +{overflow} meer
                    </span>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
