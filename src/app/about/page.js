'use client';

import AnimateIn from '../../components/AnimateIn';
import GlassCard from '../../components/GlassCard';

const stack = [
  { category: 'AI & LLMs', skills: ['LangChain', 'RAG Systems', 'Claude API', 'OpenAI', 'Vector Embeddings'] },
  { category: 'Data & Analysis', skills: ['Python', 'pandas', 'scikit-learn', 'FastAPI', 'PostgreSQL'] },
  { category: 'Frontend', skills: ['React', 'Next.js', 'Framer Motion', 'TypeScript'] },
  { category: 'Tools & Infra', skills: ['Git', 'Vercel', 'Claude Code', 'VS Code'] },
];

const contactLinks = [
  { label: 'GitHub', href: 'https://github.com' },
  { label: 'LinkedIn', href: 'https://linkedin.com' },
  { label: 'Email', href: 'mailto:hello@randy.dev' },
];

export default function AboutPage() {
  return (
    <section style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-20) var(--space-6)' }}>
      <div style={{ width: '100%', maxWidth: '960px' }}>

        <AnimateIn delay={0.05}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-10)' }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)', boxShadow: '0 0 8px rgba(232,185,49,0.7)' }} />
            <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--accent-secondary)' }}>
              SYS.PROFILE // OPERATOR
            </span>
          </div>
        </AnimateIn>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-16)', alignItems: 'start' }}>

          {/* LEFT — Bio */}
          <AnimateIn direction="left" delay={0.1}>
            <div style={{ marginBottom: 'var(--space-8)' }}>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>ABOUT</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>ME.</div>
            </div>

            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 'var(--space-4)' }}>
              I&apos;m Randy — a self-taught developer specialising in AI automation for the real estate sector. I build the systems that turn raw property data into decisions.
            </p>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 'var(--space-4)' }}>
              Ik leer het liefst door te bouwen. Elk concept dat ik interessant vind vertaalt zich in een project — zo begrijp ik het echt.
            </p>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 'var(--space-4)' }}>
              Currently exploring: automated valuation models, Dutch property data APIs, and LLM pipelines for lease contract analysis.
            </p>

            <GlassCard style={{ marginBottom: 'var(--space-8)' }}>
              <div style={{ padding: 'var(--space-4) var(--space-5)' }}>
                <p style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', margin: 0, lineHeight: 1.6 }}>
                  &ldquo;Geen buzzwords — alleen pipelines die draaien.&rdquo;
                </p>
              </div>
            </GlassCard>

            <div>
              <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
                CONTACT
              </p>
              <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
                {contactLinks.map(link => (
                  <a
                    key={link.label}
                    href={link.href}
                    style={{
                      fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', fontWeight: 700,
                      letterSpacing: '0.1em', color: 'var(--accent-secondary)', textDecoration: 'none',
                      borderBottom: '1px solid transparent',
                      transition: 'border-color var(--transition-fast), color var(--transition-fast)',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderBottomColor = 'var(--accent-primary)'; e.currentTarget.style.color = 'var(--accent-primary)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderBottomColor = 'transparent'; e.currentTarget.style.color = 'var(--accent-secondary)'; }}
                  >
                    {link.label.toUpperCase()}
                  </a>
                ))}
              </div>
            </div>
          </AnimateIn>

          {/* RIGHT — Stack */}
          <AnimateIn direction="right" delay={0.2}>
            <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-8)' }}>
              TECH STACK
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {stack.map((group, i) => (
                <GlassCard key={group.category}>
                  <div style={{ padding: 'var(--space-5)' }}>
                    <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent-secondary)', marginBottom: 'var(--space-3)' }}>
                      {group.category}
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                      {group.skills.map(skill => (
                        <span key={skill} style={{
                          padding: 'var(--space-1) var(--space-3)',
                          fontSize: 'var(--text-sm)', fontFamily: 'var(--font-heading)', fontWeight: 500,
                          color: 'var(--accent-secondary)',
                          backgroundColor: 'rgba(232,185,49,0.05)',
                          border: '1px solid rgba(232,185,49,0.18)',
                        }}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          </AnimateIn>
        </div>
      </div>
    </section>
  );
}
