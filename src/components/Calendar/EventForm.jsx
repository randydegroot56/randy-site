'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function toLocalDateTimeInputValue(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  const pad = n => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOWithTimezone(localDateTimeValue) {
  if (!localDateTimeValue) return '';
  return new Date(localDateTimeValue).toISOString();
}

const inputStyle = {
  width: '100%',
  backgroundColor: 'var(--bg-secondary)',
  border: '1px solid var(--border-default)',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-heading)',
  fontSize: 'var(--text-sm)',
  padding: 'var(--space-3) var(--space-4)',
  outline: 'none',
  boxSizing: 'border-box',
  transition: 'border-color var(--transition-fast)',
};

const labelStyle = {
  display: 'block',
  fontFamily: 'monospace',
  fontSize: '10px',
  fontWeight: 600,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: 'var(--space-2)',
};

export default function EventForm({ event, onSave, onClose, loading }) {
  const isEditing = !!event?.id;

  const defaultStart = () => {
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(d.getHours() + 1);
    return d.toISOString();
  };
  const defaultEnd = () => {
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(d.getHours() + 2);
    return d.toISOString();
  };

  const [title, setTitle] = useState(event?.summary ?? '');
  const [startDateTime, setStartDateTime] = useState(
    toLocalDateTimeInputValue(event?.start?.dateTime ?? defaultStart())
  );
  const [endDateTime, setEndDateTime] = useState(
    toLocalDateTimeInputValue(event?.end?.dateTime ?? defaultEnd())
  );
  const [description, setDescription] = useState(event?.description ?? '');
  const [location, setLocation] = useState(event?.location ?? '');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (!title.trim()) { setError('Titel is verplicht.'); return; }
    if (!startDateTime || !endDateTime) { setError('Begin- en eindtijd zijn verplicht.'); return; }
    if (new Date(endDateTime) <= new Date(startDateTime)) {
      setError('Eindtijd moet na begintijd liggen.'); return;
    }
    onSave({
      id: event?.id,
      title: title.trim(),
      startDateTime: toISOWithTimezone(startDateTime),
      endDateTime: toISOWithTimezone(endDateTime),
      description: description.trim(),
      location: location.trim(),
    });
  };

  return (
    <AnimatePresence>
      <motion.div
        key="form-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 60,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 'var(--space-6)',
        }}
      >
        <motion.div
          key="form-modal"
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.98 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          onClick={e => e.stopPropagation()}
          style={{
            width: '100%',
            maxWidth: '480px',
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderLeft: '3px solid var(--accent-primary)',
            backdropFilter: 'blur(40px)',
            WebkitBackdropFilter: 'blur(40px)',
            padding: 'var(--space-8)',
            boxShadow: 'var(--shadow-lg)',
            position: 'relative',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-6)' }}>
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
              {isEditing ? 'EVENT BEWERKEN' : 'NIEUW EVENT'}
            </span>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            {/* Title */}
            <div>
              <label style={labelStyle}>Titel *</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Event naam"
                style={inputStyle}
                onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {/* Start / End */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
              <div>
                <label style={labelStyle}>Begintijd *</label>
                <input
                  type="datetime-local"
                  value={startDateTime}
                  onChange={e => setStartDateTime(e.target.value)}
                  style={inputStyle}
                  onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                  onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
                />
              </div>
              <div>
                <label style={labelStyle}>Eindtijd *</label>
                <input
                  type="datetime-local"
                  value={endDateTime}
                  onChange={e => setEndDateTime(e.target.value)}
                  style={inputStyle}
                  onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                  onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
                />
              </div>
            </div>

            {/* Location */}
            <div>
              <label style={labelStyle}>Locatie</label>
              <input
                type="text"
                value={location}
                onChange={e => setLocation(e.target.value)}
                placeholder="Optionele locatie"
                style={inputStyle}
                onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {/* Description */}
            <div>
              <label style={labelStyle}>Omschrijving</label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Optionele omschrijving"
                rows={3}
                style={{
                  ...inputStyle,
                  resize: 'vertical',
                  fontFamily: 'var(--font-body)',
                  lineHeight: 1.6,
                }}
                onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {/* Error */}
            {error && (
              <p style={{
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                color: 'rgba(239,68,68,0.9)', margin: 0,
              }}>
                {error}
              </p>
            )}

            {/* Buttons */}
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
              <button
                type="submit"
                disabled={loading}
                style={{
                  flex: 1,
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 700, letterSpacing: '0.1em',
                  color: loading ? 'rgba(26,23,20,0.5)' : '#1A1714',
                  backgroundColor: loading ? 'rgba(232,185,49,0.4)' : 'var(--accent-primary)',
                  border: 'none', padding: 'var(--space-3) var(--space-4)',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'background-color var(--transition-fast)',
                }}
                onMouseEnter={e => { if (!loading) e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
                onMouseLeave={e => { if (!loading) e.currentTarget.style.backgroundColor = loading ? 'rgba(232,185,49,0.4)' : 'var(--accent-primary)'; }}
              >
                {loading ? 'OPSLAAN...' : 'OPSLAAN'}
              </button>
              <button
                type="button"
                onClick={onClose}
                style={{
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 600, letterSpacing: '0.1em',
                  color: 'var(--text-secondary)', backgroundColor: 'transparent',
                  border: '1px solid var(--border-default)',
                  padding: 'var(--space-3) var(--space-4)',
                  cursor: 'pointer', transition: 'border-color var(--transition-fast), color var(--transition-fast)',
                }}
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-secondary)'; }}
              >
                ANNULEREN
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
