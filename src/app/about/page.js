'use client';

import AnimateIn from '../../components/AnimateIn';

/* ── Tech stack data ─────────────────────────────────────────── */

const stack = [
  {
    category: 'Frontend',
    skills: ['React', 'Next.js', 'Vite', 'HTML/CSS', 'Framer Motion'],
  },
  {
    category: 'Backend',
    skills: ['Python', 'FastAPI', 'Node.js'],
  },
  {
    category: 'AI & Data',
    skills: ['LangChain', 'ChromaDB', 'Claude API', 'OpenAI', 'Vector Embeddings'],
  },
  {
    category: 'Tools',
    skills: ['Git', 'Claude Code', 'VS Code', 'Vercel'],
  },
];

const contactLinks = [
  { label: 'GitHub', href: 'https://github.com' },
  { label: 'LinkedIn', href: 'https://linkedin.com' },
  { label: 'Email', href: 'mailto:hello@randy.dev' },
];

/* ── Page ─────────────────────────────────────────────────────── */

export default function AboutPage() {
  return (
    <section
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-20) var(--space-6)',
      }}
    >
      <div style={{ width: '100%', maxWidth: '960px' }}>

        {/* Page label */}
        <AnimateIn delay={0.05}>
          <p
            style={{
              fontFamily: 'var(--font-heading)',
              color: 'var(--accent-secondary)',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              marginBottom: 'var(--space-10)',
            }}
          >
            Introductie
          </p>
        </AnimateIn>

        {/* Two-column grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 'var(--space-16)',
            alignItems: 'start',
          }}
        >
          {/* LEFT — Bio */}
          <AnimateIn direction="left" delay={0.1}>
            <h1
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-3xl)',
                color: 'var(--text-primary)',
                marginBottom: 'var(--space-8)',
              }}
            >
              Over mij
            </h1>

            <p
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 1.8,
                marginBottom: 'var(--space-4)',
              }}
            >
              Ik ben Randy — een developer die zichzelf heeft leren programmeren door dingen
              te bouwen. Mijn focus ligt op het toepassen van AI-tools in praktische
              projecten: van chatbots tot persoonlijke dashboards die mijn dagelijkse
              workflow verbeteren.
            </p>
            <p
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 1.8,
                marginBottom: 'var(--space-4)',
              }}
            >
              Ik leer het liefst door te bouwen. Elke tool, elke API, elk concept dat ik
              interessant vind vertaalt zich in een project. Zo begrijp ik het echt — niet
              door tutorials te kijken, maar door zelf te proberen, te falen, en opnieuw
              te beginnen.
            </p>
            <p
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 1.8,
                marginBottom: 'var(--space-10)',
              }}
            >
              Op dit moment verdiep ik me in LLM-integraties, RAG-systemen en het bouwen
              van tools die echt nuttig zijn — voor mezelf en voor anderen.
            </p>

            {/* Contact links */}
            <div>
              <p
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                Contact
              </p>
              <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
                {contactLinks.map(link => (
                  <a
                    key={link.label}
                    href={link.href}
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: 'var(--text-sm)',
                      fontWeight: 500,
                      color: 'var(--accent-secondary)',
                      textDecoration: 'none',
                      borderBottom: '1px solid transparent',
                      transition: 'border-color var(--transition-fast), color var(--transition-fast)',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderBottomColor = 'var(--accent-primary)';
                      e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderBottomColor = 'transparent';
                      e.currentTarget.style.color = 'var(--accent-secondary)';
                    }}
                  >
                    {link.label}
                  </a>
                ))}
              </div>
            </div>
          </AnimateIn>

          {/* RIGHT — Tech stack */}
          <AnimateIn direction="right" delay={0.2}>
            <h2
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-2xl)',
                color: 'var(--text-primary)',
                marginBottom: 'var(--space-8)',
              }}
            >
              Tech stack
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
              {stack.map((group, i) => (
                <div key={group.category}>
                  <p
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: 'var(--text-muted)',
                      marginBottom: 'var(--space-3)',
                    }}
                  >
                    {group.category}
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                    {group.skills.map(skill => (
                      <span
                        key={skill}
                        style={{
                          padding: 'var(--space-1) var(--space-3)',
                          borderRadius: 'var(--radius-full)',
                          fontSize: 'var(--text-sm)',
                          fontFamily: 'var(--font-heading)',
                          fontWeight: 500,
                          color: 'var(--accent-secondary)',
                          backgroundColor: 'rgba(232, 185, 49, 0.06)',
                          border: '1px solid rgba(232, 185, 49, 0.2)',
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                  {i < stack.length - 1 && (
                    <div
                      style={{
                        marginTop: 'var(--space-8)',
                        height: '1px',
                        backgroundColor: 'var(--border-subtle)',
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
          </AnimateIn>
        </div>
      </div>
    </section>
  );
}
