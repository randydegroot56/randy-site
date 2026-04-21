'use client';

import { useRef } from 'react';
import { motion } from 'framer-motion';
import AnimateIn from '../components/AnimateIn';
import StaggerChildren from '../components/StaggerChildren';
import GlassCard from '../components/GlassCard';
import { useTheme } from '../components/ThemeProvider';

/* ── Data ───────────────────────────────────────────────────── */

const capabilities = [
  {
    icon: '⬡',
    title: 'Document AI',
    desc: 'RAG pipelines for lease contracts, valuation reports & due diligence packages.',
    accent: 'full',
  },
  {
    icon: '◈',
    title: 'Market Intelligence',
    desc: 'Automated data pipelines that surface pricing trends and location insights.',
    accent: 'mid',
  },
  {
    icon: '⟳',
    title: 'Workflow Automation',
    desc: 'LLM-powered tools that eliminate repetitive broker and property manager tasks.',
    accent: 'low',
  },
];

const projects = [
  {
    title: 'Property Document AI',
    tags: ['Python', 'LangChain', 'ChromaDB', 'OpenAI'],
    status: 'Afgerond',
    statusStyle: { bg: 'rgba(34,197,94,0.10)', border: 'rgba(34,197,94,0.25)', text: 'rgba(34,197,94,0.9)', dot: 'rgba(34,197,94,0.9)' },
  },
  {
    title: 'RE Intelligence Dashboard',
    tags: ['React', 'FastAPI', 'Claude API', 'Python'],
    status: 'In ontwikkeling',
    statusStyle: { bg: 'rgba(232,185,49,0.10)', border: 'rgba(232,185,49,0.25)', text: 'var(--accent-secondary)', dot: 'var(--accent-primary)' },
  },
  {
    title: 'Automated Valuation Model',
    tags: ['Python', 'scikit-learn', 'FastAPI'],
    status: 'Concept',
    statusStyle: { bg: 'rgba(232,185,49,0.08)', border: 'rgba(232,185,49,0.2)', text: 'var(--accent-secondary)', dot: 'var(--accent-primary)' },
  },
  {
    title: 'randy.dev',
    tags: ['Next.js', 'Framer Motion', 'Canvas API'],
    status: 'Live',
    statusStyle: { bg: 'rgba(232,185,49,0.10)', border: 'rgba(232,185,49,0.25)', text: 'var(--accent-secondary)', dot: 'var(--accent-primary)' },
  },
];

/* ── Reusable section eyebrow ────────────────────────────────── */

function Eyebrow({ children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-6)' }}>
      <span style={{
        display: 'inline-block',
        width: 6, height: 6, borderRadius: '50%',
        background: 'var(--accent-primary)',
        boxShadow: '0 0 8px rgba(232,185,49,0.7)',
        flexShrink: 0,
      }} />
      <span style={{
        fontFamily: 'monospace',
        fontSize: '10px',
        fontWeight: 600,
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        color: 'var(--accent-secondary)',
      }}>
        {children}
      </span>
    </div>
  );
}

/* ── Editorial headline (3-line stacked with outline on line 3) */

function EditorialHeadline({ line1, line2, line3, size = 'var(--text-3xl)' }) {
  const lines = [
    { text: line1, outline: false },
    { text: line2, outline: false },
    { text: line3, outline: true },
  ];
  return (
    <div style={{ marginBottom: 'var(--space-8)' }}>
      {lines.map(({ text, outline }, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: 'var(--font-heading)',
            fontSize: size,
            fontWeight: 900,
            lineHeight: 0.92,
            letterSpacing: '-0.03em',
            ...(outline
              ? {
                  color: 'transparent',
                  WebkitTextStroke: '1px rgba(232,185,49,0.5)',
                }
              : { color: 'var(--text-primary)' }),
          }}
        >
          {text}
        </motion.div>
      ))}
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────────── */

export default function Page() {
  const photoRef = useRef(null);
  const textRef  = useRef(null);
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  function handleHeroMouseMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const cx = (e.clientX - rect.left) / rect.width  - 0.5;
    const cy = (e.clientY - rect.top)  / rect.height - 0.5;
    if (photoRef.current) {
      photoRef.current.style.transform = `translate(${cx * 38}px, ${cy * 22}px)`;
    }
    if (textRef.current) {
      textRef.current.style.transform = `translate(${cx * -14}px, ${cy * -9}px)`;
    }
  }

  function handleHeroMouseLeave() {
    [photoRef, textRef].forEach((ref) => {
      if (!ref.current) return;
      ref.current.style.transition = 'transform 0.6s ease';
      ref.current.style.transform  = 'translate(0,0)';
      setTimeout(() => {
        if (ref.current) ref.current.style.transition = 'transform 0.1s linear';
      }, 600);
    });
  }

  return (
    <div className="homepage-scroll">

      {/* ─────────────────────────────────────────────────────── */}
      {/* SECTION 1 — HERO                                       */}
      {/* ─────────────────────────────────────────────────────── */}
      <section
        className="snap-section"
        onMouseMove={handleHeroMouseMove}
        onMouseLeave={handleHeroMouseLeave}
        style={{
          height: 'calc(100vh - 4rem)',
          minHeight: 'unset',
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Layer 0: Photo */}
        <div
          ref={photoRef}
          style={{
            position: 'absolute',
            inset: '-10% -5%',
            backgroundImage: "url('/herofoto.jpeg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            filter: `brightness(${isDark ? '0.65' : '0.80'}) saturate(0.75)`,
            willChange: 'transform',
            transition: 'transform 0.1s linear',
          }}
        />

        {/* Layer 1: Gold tint wash */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(135deg, rgba(232,185,49,0.06) 0%, transparent 50%, rgba(232,185,49,0.03) 100%)',
            pointerEvents: 'none',
          }}
        />

        {/* Layer 2: Readability gradient scrim */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, rgba(12,10,8,0.88) 0%, rgba(12,10,8,0.72) 30%, rgba(12,10,8,0.22) 65%, transparent 100%)',
            pointerEvents: 'none',
            zIndex: 1,
          }}
        />

        {/* Layer 3: Text content */}
        <div
          ref={textRef}
          className="container"
          style={{
            position: 'relative',
            zIndex: 10,
            paddingTop: 'var(--space-16)',
            paddingBottom: 'var(--space-16)',
            willChange: 'transform',
            transition: 'transform 0.1s linear',
          }}
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.15 }}
          >
            <Eyebrow>Real Estate × AI Automation</Eyebrow>
          </motion.div>

          <EditorialHeadline
            line1="I BUILD AI TOOLS"
            line2="THAT AUTOMATE"
            line3="REAL ESTATE WORKFLOWS."
            size="clamp(2rem, 5.5vw, var(--text-4xl))"
          />

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.8, ease: 'easeOut' }}
            style={{
              color: 'var(--text-secondary)',
              fontSize: 'var(--text-md)',
              lineHeight: 1.7,
              maxWidth: '520px',
              marginBottom: 'var(--space-10)',
              textShadow: '0 1px 12px rgba(18,17,16,0.9)',
            }}
          >
            From property document analysis to market intelligence — I build the AI pipelines
            that save hours of manual work for real estate professionals.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 1.0, ease: 'easeOut' }}
            style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}
          >
            <a
              href="/work"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)',
                padding: 'var(--space-3) var(--space-8)',
                backgroundColor: 'var(--accent-primary)',
                color: '#121110',
                fontFamily: 'var(--font-heading)',
                fontWeight: 700,
                fontSize: 'var(--text-xs)',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                textDecoration: 'none',
                transition: 'background-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)';
                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = 'var(--accent-primary)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              VIEW PROJECTS →
            </a>
            <a
              href="/about"
              style={{
                display: 'inline-flex', alignItems: 'center',
                padding: 'var(--space-3) var(--space-8)',
                backgroundColor: 'transparent',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-heading)',
                fontWeight: 600,
                fontSize: 'var(--text-xs)',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                textDecoration: 'none',
                border: '1px solid var(--border-default)',
                transition: 'border-color var(--transition-fast), color var(--transition-fast)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'rgba(232,185,49,0.4)';
                e.currentTarget.style.color = 'var(--text-primary)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border-default)';
                e.currentTarget.style.color = 'var(--text-secondary)';
              }}
            >
              ABOUT ME
            </a>
          </motion.div>
        </div>

        {/* Scroll indicator — scan line */}
        <style>{`
          @keyframes scanLine {
            0%   { transform: translateX(-100%); }
            50%  { transform: translateX(100%); }
            100% { transform: translateX(100%); }
          }
        `}</style>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4, duration: 0.6 }}
          style={{
            position: 'absolute',
            bottom: 'var(--space-8)',
            left: '80px',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div style={{ width: 32, height: 1, background: 'rgba(232,185,49,0.4)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', inset: 0, background: '#E8B931', animation: 'scanLine 1.8s ease-in-out infinite' }} />
          </div>
          <span style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(237,232,220,0.3)' }}>
            Scroll to explore
          </span>
        </motion.div>
      </section>

      <div style={{ height: '45vh' }} />

      {/* ─────────────────────────────────────────────────────── */}
      {/* SECTION 2 — CAPABILITIES                               */}
      {/* ─────────────────────────────────────────────────────── */}
      <section id="capabilities" className="snap-section">
        <div className="container">
          <AnimateIn delay={0.05}>
            <Eyebrow>MODULE_02 // CAPABILITIES</Eyebrow>
            <div style={{ marginBottom: 'var(--space-8)' }}>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>WHAT I</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>BUILD</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>FOR REAL ESTATE.</div>
            </div>
          </AnimateIn>

          <StaggerChildren style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-4)' }}>
            {capabilities.map(cap => (
              <GlassCard key={cap.title}>
                <div style={{ padding: 'var(--space-6)' }}>
                  <div style={{ fontFamily: 'monospace', fontSize: '20px', color: 'var(--accent-primary)', marginBottom: 'var(--space-4)', opacity: 0.8 }}>{cap.icon}</div>
                  <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 'var(--text-base)', color: 'var(--text-primary)', marginBottom: 'var(--space-2)', letterSpacing: '0.02em' }}>{cap.title}</div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.65, margin: 0 }}>{cap.desc}</p>
                </div>
              </GlassCard>
            ))}
          </StaggerChildren>
        </div>
      </section>

      <div style={{ height: '45vh' }} />

      {/* ─────────────────────────────────────────────────────── */}
      {/* SECTION 3 — PROJECTS                                   */}
      {/* ─────────────────────────────────────────────────────── */}
      <section id="projects" className="snap-section">
        <div className="container">
          <AnimateIn delay={0.05}>
            <Eyebrow>MODULE_03 // SYSTEMS</Eyebrow>
            <div style={{ marginBottom: 'var(--space-8)' }}>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>BUILT</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>PROJECTS.</div>
            </div>
          </AnimateIn>

          <StaggerChildren style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginBottom: 'var(--space-8)' }}>
            {projects.map(project => (
              <GlassCard key={project.title}>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  gap: 'var(--space-4)',
                  padding: 'var(--space-4) var(--space-4)',
                  borderBottom: '1px solid rgba(232,185,49,0.06)',
                }}>
                  <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 'var(--text-base)', color: 'var(--text-primary)', minWidth: 0 }}>
                    {project.title}
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', flex: 1, justifyContent: 'center' }}>
                    {project.tags.map(tag => (
                      <span key={tag} style={{
                        padding: '0.15rem var(--space-2)', fontFamily: 'var(--font-heading)', fontWeight: 500,
                        fontSize: 'var(--text-xs)', color: 'var(--text-muted)',
                        backgroundColor: 'rgba(232,185,49,0.04)', border: '1px solid rgba(232,185,49,0.1)',
                      }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                  <span style={{
                    flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
                    padding: '0.2rem var(--space-3)',
                    fontSize: 'var(--text-xs)', fontFamily: 'var(--font-heading)', fontWeight: 600,
                    backgroundColor: project.statusStyle.bg,
                    color: project.statusStyle.text,
                    border: `1px solid ${project.statusStyle.border}`,
                  }}>
                    <span style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: project.statusStyle.dot, display: 'inline-block' }} />
                    {project.status}
                  </span>
                </div>
              </GlassCard>
            ))}
          </StaggerChildren>

          <a
            href="/work"
            style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: 'var(--accent-secondary)', textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)',
              transition: 'color var(--transition-fast)',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--accent-secondary)'; }}
          >
            VIEW ALL PROJECTS →
          </a>
        </div>
      </section>

      <div style={{ height: '45vh' }} />

      {/* ─────────────────────────────────────────────────────── */}
      {/* SECTION 4 — ABOUT SNIPPET                              */}
      {/* ─────────────────────────────────────────────────────── */}
      <section id="about" className="snap-section">
        <div className="container">
          <AnimateIn delay={0.05}>
            <Eyebrow>SYS.PROFILE // OPERATOR</Eyebrow>
            <div style={{ marginBottom: 'var(--space-6)' }}>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>SELF-TAUGHT.</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>SYSTEMS-FOCUSED.</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-2xl)', fontWeight: 900, lineHeight: 0.95, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>PROPTECH-DRIVEN.</div>
            </div>

            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.75, maxWidth: '540px', marginBottom: 'var(--space-3)' }}>
              I build AI systems that save real estate professionals hours of manual work.
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.75, maxWidth: '540px', marginBottom: 'var(--space-8)' }}>
              Geen buzzwords — alleen pipelines die draaien.
            </p>

            {/* Stat blocks */}
            <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', marginBottom: 'var(--space-8)' }}>
              {[
                { val: '4+', label: 'PROJECTS' },
                { val: 'RAG', label: 'SPECIALIST' },
                { val: 'NL', label: 'MARKET' },
              ].map(({ val, label }) => (
                <div key={label} style={{
                  textAlign: 'center',
                  border: '1px solid rgba(232,185,49,0.15)',
                  padding: 'var(--space-4) var(--space-6)',
                }}>
                  <div style={{ fontFamily: 'monospace', fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--accent-primary)' }}>{val}</div>
                  <div style={{ fontFamily: 'var(--font-heading)', fontSize: '9px', fontWeight: 600, letterSpacing: '0.14em', color: 'var(--text-muted)', marginTop: '2px' }}>{label}</div>
                </div>
              ))}
            </div>

            <a
              href="/about"
              style={{
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', fontWeight: 700,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: 'var(--accent-secondary)', textDecoration: 'none',
                display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--accent-secondary)'; }}
            >
              → FULL PROFILE
            </a>
          </AnimateIn>
        </div>
      </section>

      <div style={{ height: '45vh' }} />

      {/* ─────────────────────────────────────────────────────── */}
      {/* SECTION 5 — CTA                                        */}
      {/* ─────────────────────────────────────────────────────── */}
      <section className="snap-section">
        <div className="container" style={{ textAlign: 'center' }}>
          <AnimateIn delay={0.05}>
            <Eyebrow>MODULE_05 // CONTACT</Eyebrow>
            <div style={{ marginBottom: 'var(--space-6)' }}>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(1.8rem, 4vw, var(--text-3xl))', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>READY TO</div>
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(1.8rem, 4vw, var(--text-3xl))', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.6)', marginBottom: 'var(--space-2)' }}>AUTOMATE?</div>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.7, maxWidth: '440px', margin: '0 auto var(--space-10)' }}>
              Let&apos;s talk about what AI can do for your real estate workflow.
            </p>
            <a
              href="mailto:hello@randy.dev"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)',
                padding: 'var(--space-4) var(--space-12)',
                backgroundColor: 'var(--accent-primary)',
                color: '#121110',
                fontFamily: 'var(--font-heading)',
                fontWeight: 800,
                fontSize: 'var(--text-xs)',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                textDecoration: 'none',
                transition: 'background-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)';
                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = 'var(--accent-primary)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              GET IN TOUCH →
            </a>
          </AnimateIn>
        </div>
      </section>

    </div>
  );
}
