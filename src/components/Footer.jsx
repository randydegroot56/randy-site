'use client';

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: 'var(--space-10) 0 var(--space-8)',
        marginTop: 'auto',
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-6)',
        }}
      >
        {/* Top row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--space-4)',
          }}
        >
          {/* Logo */}
          <span
            style={{
              fontFamily: 'var(--font-heading)',
              fontWeight: 700,
              fontSize: 'var(--text-base)',
              color: 'var(--text-muted)',
            }}
          >
            randy<span style={{ color: 'var(--accent-primary)' }}>.</span>dev
          </span>

          {/* External links */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)' }}>
            {[
              { label: 'GitHub',   href: '#' },
              { label: 'LinkedIn', href: '#' },
            ].map(({ label, href }) => (
              <a
                key={label}
                href={href}
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 500,
                  color: 'var(--text-muted)',
                  textDecoration: 'none',
                  transition: 'color var(--transition-base)',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
              >
                {label}
              </a>
            ))}
          </nav>
        </div>

        {/* Copyright */}
        <p
          style={{
            fontFamily: 'var(--font-heading)',
            fontSize: 'var(--text-xs)',
            color: 'var(--text-muted)',
            marginBottom: 0,
          }}
        >
          &copy; {new Date().getFullYear()} randy.dev — Gebouwd met Next.js
        </p>
      </div>
    </footer>
  );
}
