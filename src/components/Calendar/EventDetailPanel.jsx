'use client';

import { motion, AnimatePresence } from 'framer-motion';

function formatDateTime(event) {
  if (event.start?.dateTime) {
    const start = new Date(event.start.dateTime);
    const end = new Date(event.end.dateTime);
    const dateStr = start.toLocaleDateString('nl-NL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    const startTime = start.toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });
    const endTime = end.toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });
    return { date: dateStr, time: `${startTime} – ${endTime}` };
  }
  if (event.start?.date) {
    const d = new Date(event.start.date);
    return {
      date: d.toLocaleDateString('nl-NL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
      time: 'Hele dag',
    };
  }
  return { date: '—', time: '—' };
}

export default function EventDetailPanel({ event, onClose, onEdit, onDelete }) {
  if (!event) return null;

  const { date, time } = formatDateTime(event);

  return (
    <AnimatePresence>
      {event && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 50,
              backgroundColor: 'rgba(0,0,0,0.3)',
            }}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            style={{
              position: 'fixed',
              top: '50%', right: 'var(--space-6)',
              transform: 'translateY(-50%)',
              zIndex: 51,
              width: '320px',
              maxWidth: 'calc(100vw - var(--space-12))',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderLeft: '3px solid var(--accent-primary)',
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
              padding: 'var(--space-8)',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            {/* Close button */}
            <button
              onClick={onClose}
              style={{
                position: 'absolute', top: 'var(--space-4)', right: 'var(--space-4)',
                background: 'none', border: 'none',
                color: 'var(--text-muted)', cursor: 'pointer',
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-lg)',
                lineHeight: 1, padding: 'var(--space-1)',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; }}
            >
              ×
            </button>

            {/* Tag */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-4)' }}>
              <span style={{
                display: 'inline-block', width: 6, height: 6,
                borderRadius: '50%', background: 'var(--accent-primary)',
                boxShadow: '0 0 6px rgba(232,185,49,0.6)',
              }} />
              <span style={{
                fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
                letterSpacing: '0.15em', textTransform: 'uppercase',
                color: 'var(--accent-secondary)',
              }}>
                RDG.DEV EVENT
              </span>
            </div>

            {/* Title */}
            <h3 style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-lg)',
              fontWeight: 700, color: 'var(--text-primary)',
              letterSpacing: '-0.01em', marginBottom: 'var(--space-5)',
              paddingRight: 'var(--space-8)',
            }}>
              {event.summary || '(Geen titel)'}
            </h3>

            {/* Date & time */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{
                fontFamily: 'monospace', fontSize: 'var(--text-xs)',
                color: 'var(--text-muted)', marginBottom: 'var(--space-1)',
                letterSpacing: '0.06em', textTransform: 'capitalize',
              }}>
                {date}
              </p>
              <p style={{
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-base)',
                color: 'var(--accent-secondary)', fontWeight: 600,
              }}>
                {time}
              </p>
            </div>

            {/* Location */}
            {event.location && (
              <div style={{ marginBottom: 'var(--space-4)' }}>
                <p style={{
                  fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  color: 'var(--text-muted)', marginBottom: 'var(--space-1)',
                }}>
                  LOCATIE
                </p>
                <p style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                  {event.location}
                </p>
              </div>
            )}

            {/* Description */}
            {event.description && (
              <div style={{ marginBottom: 'var(--space-6)' }}>
                <p style={{
                  fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  color: 'var(--text-muted)', marginBottom: 'var(--space-1)',
                }}>
                  OMSCHRIJVING
                </p>
                <p style={{
                  fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)',
                  color: 'var(--text-secondary)', lineHeight: 1.6,
                }}>
                  {event.description}
                </p>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-6)' }}>
              <button
                onClick={() => onEdit(event)}
                style={{
                  flex: 1,
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 700, letterSpacing: '0.1em',
                  color: '#1A1714', backgroundColor: 'var(--accent-primary)',
                  border: 'none', padding: 'var(--space-2) var(--space-4)',
                  cursor: 'pointer', transition: 'background-color var(--transition-fast)',
                }}
                onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
              >
                BEWERKEN
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`"${event.summary}" verwijderen?`)) onDelete(event.id);
                }}
                style={{
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 700, letterSpacing: '0.1em',
                  color: 'rgba(239,68,68,0.8)', backgroundColor: 'transparent',
                  border: '1px solid rgba(239,68,68,0.3)',
                  padding: 'var(--space-2) var(--space-4)',
                  cursor: 'pointer', transition: 'border-color var(--transition-fast), color var(--transition-fast)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'rgba(239,68,68,0.7)';
                  e.currentTarget.style.color = 'rgba(239,68,68,1)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'rgba(239,68,68,0.3)';
                  e.currentTarget.style.color = 'rgba(239,68,68,0.8)';
                }}
              >
                VERWIJDEREN
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
