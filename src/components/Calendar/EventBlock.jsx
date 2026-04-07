'use client';

export default function EventBlock({ event, onClick, compact = true }) {
  const title = event.summary || '(Geen titel)';
  const isAllDay = !event.start?.dateTime;
  const time = isAllDay
    ? 'Hele dag'
    : new Date(event.start.dateTime).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });

  return (
    <div
      onClick={() => onClick(event)}
      title={`${time} — ${title}`}
      style={{
        backgroundColor: 'var(--accent-primary)',
        color: 'var(--bg-primary)',
        padding: compact ? '2px var(--space-2)' : 'var(--space-2) var(--space-3)',
        borderRadius: 'var(--radius-sm)',
        fontSize: 'var(--text-xs)',
        fontFamily: 'var(--font-heading)',
        fontWeight: 600,
        cursor: 'pointer',
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
        userSelect: 'none',
        transition: 'background-color var(--transition-fast)',
        marginBottom: compact ? '2px' : 0,
      }}
      onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
      onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
    >
      {compact ? `${time} ${title}` : title}
    </div>
  );
}
