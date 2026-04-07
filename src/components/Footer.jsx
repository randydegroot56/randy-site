'use client';

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: '1px solid rgba(232,185,49,0.08)',
        padding: 'var(--space-8) 0',
        marginTop: 'auto',
        position: 'relative',
        zIndex: 6,
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
        }}
      >
        {/* Logo */}
        <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--accent-primary)', letterSpacing: '0.05em' }}>
          RDG<span style={{ color: 'rgba(232,185,49,0.4)' }}>.</span>
        </span>

        {/* Copyright */}
        <p style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', margin: 0 }}>
          © {new Date().getFullYear()} — REAL ESTATE AI AUTOMATION
        </p>

        {/* Links */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)' }}>
          {[{ label: 'GITHUB', href: '#' }, { label: 'LINKEDIN', href: '#' }].map(({ label, href }) => (
            <a
              key={label}
              href={href}
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.12em',
                color: 'var(--text-muted)',
                textDecoration: 'none',
                transition: 'color var(--transition-base)',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-secondary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              {label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  );
}
