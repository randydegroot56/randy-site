'use client';

import { useState } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';

function getWeekStart(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - (day + 6) % 7);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getPeriodLabel(view, currentDate) {
  if (view === 'month') {
    return currentDate.toLocaleString('nl-NL', { month: 'long', year: 'numeric' });
  }
  const monday = getWeekStart(currentDate);
  const sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);
  const startLabel = monday.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' });
  const endLabel = sunday.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short', year: 'numeric' });
  return `${startLabel} — ${endLabel}`;
}

export default function CalendarHeader({ view, onViewChange, currentDate, onPrev, onNext, onNewEvent }) {
  const [hoveredView, setHoveredView] = useState(null);
  const label = getPeriodLabel(view, currentDate);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 'var(--space-6)',
      flexWrap: 'wrap',
      gap: 'var(--space-4)',
    }}>

      {/* Left: prev / next */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {[{ label: '←', action: onPrev }, { label: '→', action: onNext }].map(({ label: btn, action }) => (
          <button
            key={btn}
            onClick={action}
            style={{
              width: '2rem', height: '2rem',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              backgroundColor: 'transparent',
              border: '1px solid rgba(232,185,49,0.2)',
              color: 'var(--accent-secondary)',
              fontFamily: 'var(--font-heading)',
              fontSize: 'var(--text-base)',
              cursor: 'pointer',
              transition: 'border-color var(--transition-fast), color var(--transition-fast)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--accent-primary)';
              e.currentTarget.style.color = 'var(--accent-primary)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'rgba(232,185,49,0.2)';
              e.currentTarget.style.color = 'var(--accent-secondary)';
            }}
          >
            {btn}
          </button>
        ))}
      </div>

      {/* Center: period label */}
      <h2 style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 'var(--text-xl)',
        fontWeight: 700,
        color: 'var(--text-primary)',
        letterSpacing: '-0.02em',
        margin: 0,
        textTransform: 'capitalize',
      }}>
        {label}
      </h2>

      {/* Right: view toggle + new event button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)' }}>
        <LayoutGroup id="cal-view-toggle">
          <div style={{ display: 'flex', gap: 'var(--space-5)' }}>
            {[{ id: 'month', label: 'MAAND' }, { id: 'week', label: 'WEEK' }].map(v => (
              <div
                key={v.id}
                style={{ position: 'relative', cursor: 'pointer', paddingBottom: 'var(--space-1)' }}
                onClick={() => onViewChange(v.id)}
                onMouseEnter={() => setHoveredView(v.id)}
                onMouseLeave={() => setHoveredView(null)}
              >
                <span style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  letterSpacing: '0.12em',
                  color: view === v.id || hoveredView === v.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  transition: 'color var(--transition-fast)',
                }}>
                  {v.label}
                </span>

                <AnimatePresence>
                  {hoveredView === v.id && view !== v.id && (
                    <motion.span
                      key="hover-underline"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      exit={{ scaleX: 0 }}
                      transition={{ duration: 0.2, ease: 'easeOut' }}
                      style={{
                        position: 'absolute', bottom: 0, left: 0, right: 0,
                        height: '1px', backgroundColor: 'var(--accent-primary)',
                        transformOrigin: 'left',
                      }}
                    />
                  )}
                </AnimatePresence>

                {view === v.id && (
                  <motion.span
                    layoutId="cal-underline"
                    style={{
                      position: 'absolute', bottom: 0, left: 0, right: 0,
                      height: '1px', backgroundColor: 'var(--accent-primary)',
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </LayoutGroup>

        <button
          onClick={onNewEvent}
          style={{
            fontFamily: 'var(--font-heading)',
            fontSize: 'var(--text-xs)',
            fontWeight: 700,
            letterSpacing: '0.1em',
            color: 'var(--bg-primary)',
            backgroundColor: 'var(--accent-primary)',
            border: 'none',
            padding: 'var(--space-2) var(--space-4)',
            cursor: 'pointer',
            transition: 'background-color var(--transition-fast)',
          }}
          onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
        >
          + EVENT
        </button>
      </div>
    </div>
  );
}
