'use client';

import { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import AnimateIn from '../components/AnimateIn';
import StaggerChildren from '../components/StaggerChildren';
import ParallaxBackground from '../components/ParallaxBackground';
import { useTheme } from '../components/ThemeProvider';

/* ============================================================
   PROJECT DATA
   ============================================================ */

const projects = [
  {
    title: 'RAG Chatbot',
    description:
      'Een intelligente chatbot die PDF documenten doorzoekt met vector embeddings. Upload een PDF, stel vragen, en krijg antwoorden inclusief bronverwijzingen.',
    tags: ['Python', 'LangChain', 'ChromaDB', 'OpenAI'],
    status: 'Afgerond',
    statusStyle: {
      bg: 'rgba(34, 197, 94, 0.12)',
      border: 'rgba(34, 197, 94, 0.28)',
      text: 'rgba(34, 197, 94, 0.95)',
      dot: 'rgba(34, 197, 94, 0.9)',
    },
  },
  {
    title: 'Personal Command Center',
    description:
      'Een persoonlijk dashboard met AI-gegenereerde briefings, weer, taken en nieuws. Dagelijks startpunt met real-time data.',
    tags: ['React', 'FastAPI', 'Claude API', 'Python'],
    status: 'In ontwikkeling',
    statusStyle: {
      bg: 'rgba(232, 185, 49, 0.12)',
      border: 'rgba(232, 185, 49, 0.30)',
      text: 'var(--accent-secondary)',
      dot: 'var(--accent-primary)',
    },
  },
  {
    title: 'randy.dev',
    description:
      'Deze website — van scratch gebouwd met Next.js. Custom theming, Framer Motion animaties en een generatief 3D netwerk-achtergrond.',
    tags: ['Next.js', 'React', 'Framer Motion', 'Canvas API'],
    status: 'Live',
    statusStyle: {
      bg: 'rgba(232, 185, 49, 0.12)',
      border: 'rgba(232, 185, 49, 0.30)',
      text: 'var(--accent-secondary)',
      dot: 'var(--accent-primary)',
    },
  },
];

/* ============================================================
   LATEST BLOG POSTS (2 newest)
   ============================================================ */

const latestPosts = [
  {
    date: '28 maart 2026',
    readTime: '8 min',
    title: 'Hoe ik mijn eerste RAG chatbot bouwde',
    preview:
      'Van PDF naar antwoord — een deep dive in embeddings, vector databases, en waarom context alles is.',
    href: '/blog',
  },
  {
    date: '15 maart 2026',
    readTime: '5 min',
    title: 'Claude Code als development partner',
    preview:
      'Mijn ervaringen met AI-assisted coding: wat werkt, wat niet, en hoe je het beste uit Claude Code haalt.',
    href: '/blog',
  },
];

/* ============================================================
   GLASS CARD (parallax + theme-aware frosted glass)
   ============================================================ */

function GlassCard({ children, variant = 'default' }) {
  const { theme } = useTheme();
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  });
  const y = useTransform(scrollYProgress, [0, 1], [30, -30]);
  const opacityFade = useTransform(scrollYProgress, [0, 0.10, 0.90, 1], [0, 1, 1, 0]);
  const isDark = theme === 'dark';

  const bgMap = {
    hero:    { dark: 'rgba(18, 17, 16, 0.002)', light: 'rgba(251, 248, 240, 0.003)' },
    tinted:  { dark: 'rgba(42, 38, 34, 0.003)', light: 'rgba(240, 234, 219, 0.004)' },
    plain:   { dark: 'rgba(18, 17, 16, 0.002)', light: 'rgba(251, 248, 240, 0.003)' },
    default: { dark: 'rgba(42, 38, 34, 0.003)', light: 'rgba(255, 255, 255, 0.004)' },
  };
  const bg = bgMap[variant][isDark ? 'dark' : 'light'];

  return (
    <motion.div
      ref={ref}
      style={{
        y,
        opacity: variant === 'hero' ? 1 : opacityFade,
        background: `linear-gradient(to right, transparent 6px, var(--accent-primary) 6px, var(--accent-primary) 8px, transparent 8px), ${bg}`,
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        boxShadow: isDark ? 'none' : '0 8px 32px rgba(26,23,20,0.03)',
        width: '50%',
        marginLeft: 'var(--space-12)',
        padding: 'var(--space-24) var(--space-16)',
        position: 'relative',
        zIndex: 1,
        ...(variant === 'hero' && {
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: 0,
          width: '100%',
          marginLeft: 0,
        }),
      }}
    >
      {children}
    </motion.div>
  );
}

/* ============================================================
   CHEVRON SVG
   ============================================================ */

function ChevronSVG() {
  return (
    <svg width="28" height="16" viewBox="0 0 28 16" fill="none">
      <path
        d="M2 2l12 12L26 2"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ============================================================
   PAGE COMPONENT
   ============================================================ */

export default function Page() {
  return (
    <div className="homepage-scroll">

      {/* ── HERO ─────────────────────────────────────────────── */}
      <section
        className="snap-section"
        style={{
          height: 'calc(100vh - 4rem)',
          minHeight: 'unset',
          padding: 0,
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Parallax glow circle */}
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
          <ParallaxBackground speed={0.3}>
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '600px',
                height: '600px',
                borderRadius: '50%',
                background:
                  'radial-gradient(circle, rgba(232,185,49,0.12) 0%, rgba(232,185,49,0.04) 40%, transparent 70%)',
                filter: 'blur(40px)',
              }}
            />
          </ParallaxBackground>
        </div>

        <GlassCard variant="hero">
          <AnimateIn delay={0.1}>
            <div className="container" style={{ position: 'relative', zIndex: 1, padding: 'var(--space-24) var(--space-16)' }}>
              <p
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 500,
                  color: 'var(--accent-secondary)',
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  marginBottom: 'var(--space-6)',
                }}
              >
                Full-stack developer & AI enthousiast
              </p>

              <h1
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'clamp(2.2rem, 6vw, var(--text-4xl))',
                  fontWeight: 700,
                  lineHeight: 1.1,
                  letterSpacing: '-0.03em',
                  marginBottom: 'var(--space-6)',
                  color: 'var(--text-primary)',
                }}
              >
                Ik bouw dingen{' '}
                <span
                  style={{
                    background:
                      'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 50%, var(--accent-tertiary) 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  die werken
                </span>
              </h1>

              <p
                style={{
                  fontSize: 'var(--text-md)',
                  color: 'var(--text-secondary)',
                  maxWidth: '560px',
                  marginInline: 'auto',
                  marginBottom: 'var(--space-10)',
                  lineHeight: 1.7,
                }}
              >
                Van AI-chatbots tot productie-klare webapplicaties — ik combineer technische
                precisie met een oog voor detail.
              </p>

              <div
                style={{
                  display: 'flex',
                  gap: 'var(--space-4)',
                  justifyContent: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <a
                  href="/work"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    padding: 'var(--space-3) var(--space-8)',
                    borderRadius: 'var(--radius-full)',
                    backgroundColor: 'var(--accent-primary)',
                    color: '#121110',
                    fontFamily: 'var(--font-heading)',
                    fontWeight: 600,
                    fontSize: 'var(--text-base)',
                    transition: 'background-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast)',
                    boxShadow: 'var(--shadow-sm)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.backgroundColor = 'var(--accent-primary)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  Bekijk projecten
                </a>
                <a
                  href="/about"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: 'var(--space-3) var(--space-8)',
                    borderRadius: 'var(--radius-full)',
                    backgroundColor: 'transparent',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-heading)',
                    fontWeight: 500,
                    fontSize: 'var(--text-base)',
                    border: '1px solid var(--border-default)',
                    transition: 'border-color var(--transition-fast), background-color var(--transition-fast)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.backgroundColor = 'var(--bg-secondary)';
                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.borderColor = 'var(--border-default)';
                  }}
                >
                  Over mij
                </a>
              </div>
            </div>
          </AnimateIn>

          {/* Scroll chevrons */}
          <motion.button
            onClick={() =>
              document.getElementById('over-mij')?.scrollIntoView({ behavior: 'smooth' })
            }
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              position: 'absolute',
              bottom: 'var(--space-8)',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '2px',
              color: 'var(--accent-primary)',
              opacity: 0.7,
              zIndex: 2,
              filter: 'drop-shadow(0 0 3px rgba(232,185,49,0.3))',
            }}
            whileHover={{
              opacity: 1,
              scale: 1.2,
              filter: 'drop-shadow(0 0 8px rgba(232,185,49,0.9)) drop-shadow(0 0 16px rgba(232,185,49,0.4))',
            }}
            aria-label="Scroll naar volgende sectie"
          >
            <ChevronSVG />
            <ChevronSVG />
          </motion.button>
        </GlassCard>
      </section>

      {/* spacer */}
      <div style={{ height: '45vh' }} />

      {/* ── ABOUT PREVIEW ────────────────────────────────────── */}
      <section id="over-mij" className="snap-section">
        <AnimateIn delay={0.1}>
          <GlassCard variant="plain">
            <p
              style={{
                fontFamily: 'var(--font-heading)',
                color: 'var(--accent-secondary)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                marginBottom: 'var(--space-4)',
              }}
            >
              Over mij
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-2xl)',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: 'var(--space-6)',
              }}
            >
              Developer. Leerling. Bouwer.
            </h2>
            <p
              style={{
                color: 'var(--text-secondary)',
                fontSize: 'var(--text-md)',
                lineHeight: 1.8,
                marginBottom: 'var(--space-4)',
                maxWidth: '520px',
              }}
            >
              Ik ben Randy — een developer die zichzelf heeft leren programmeren door dingen
              te bouwen. Mijn focus ligt op AI-gedreven applicaties en full-stack projecten
              die echt iets oplossen.
            </p>
            <p
              style={{
                color: 'var(--text-secondary)',
                fontSize: 'var(--text-md)',
                lineHeight: 1.8,
                marginBottom: 'var(--space-10)',
                maxWidth: '520px',
              }}
            >
              Elke tool en elke API die ik interessant vind vertaalt zich in een project.
              Zo leer ik het beste.
            </p>
            <a
              href="/about"
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--accent-secondary)'; }}
            >
              Meer over mij →
            </a>
          </GlassCard>
        </AnimateIn>
      </section>

      {/* spacer */}
      <div style={{ height: '45vh' }} />

      {/* ── PROJECTS ─────────────────────────────────────────── */}
      <section id="projecten" className="snap-section">
        <AnimateIn delay={0.1}>
          <GlassCard variant="tinted">
            <p
              style={{
                fontFamily: 'var(--font-heading)',
                color: 'var(--accent-secondary)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                marginBottom: 'var(--space-4)',
              }}
            >
              Portfolio
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-2xl)',
                fontWeight: 600,
                marginBottom: 'var(--space-2)',
                color: 'var(--text-primary)',
              }}
            >
              Projecten
            </h2>
            <p
              style={{
                color: 'var(--text-muted)',
                marginBottom: 'var(--space-10)',
                fontSize: 'var(--text-sm)',
              }}
            >
              Een selectie van wat ik gebouwd heb.
            </p>

            <StaggerChildren
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                gap: 'var(--space-6)',
                marginBottom: 'var(--space-10)',
              }}
            >
              {projects.map(project => (
                <motion.article
                  key={project.title}
                  whileHover={{
                    y: -6,
                    boxShadow: 'var(--shadow-glow)',
                    borderColor: 'var(--accent-primary)',
                  }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderRadius: 'var(--radius-xl)',
                    padding: 'var(--space-6)',
                    border: '1px solid var(--border-subtle)',
                    boxShadow: 'var(--shadow-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 'var(--space-3)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
                    <h3
                      style={{
                        fontFamily: 'var(--font-heading)',
                        fontSize: 'var(--text-lg)',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {project.title}
                    </h3>
                    <span
                      style={{
                        flexShrink: 0,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 'var(--space-1)',
                        padding: '0.2rem var(--space-2)',
                        borderRadius: 'var(--radius-full)',
                        fontSize: 'var(--text-xs)',
                        fontFamily: 'var(--font-heading)',
                        fontWeight: 600,
                        backgroundColor: project.statusStyle.bg,
                        color: project.statusStyle.text,
                        border: `1px solid ${project.statusStyle.border}`,
                      }}
                    >
                      <span style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: project.statusStyle.dot, display: 'inline-block' }} />
                      {project.status}
                    </span>
                  </div>

                  <p
                    style={{
                      color: 'var(--text-secondary)',
                      fontSize: 'var(--text-sm)',
                      lineHeight: 1.7,
                      flex: 1,
                      marginBottom: 0,
                    }}
                  >
                    {project.description}
                  </p>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                    {project.tags.map(tag => (
                      <span
                        key={tag}
                        style={{
                          padding: '0.15rem var(--space-2)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-xs)',
                          fontFamily: 'var(--font-heading)',
                          fontWeight: 500,
                          backgroundColor: 'var(--bg-secondary)',
                          color: 'var(--text-muted)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </motion.article>
              ))}
            </StaggerChildren>

            <a
              href="/work"
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--accent-secondary)'; }}
            >
              Bekijk alle projecten →
            </a>
          </GlassCard>
        </AnimateIn>
      </section>

      {/* spacer */}
      <div style={{ height: '45vh' }} />

      {/* ── LATEST BLOG POSTS ────────────────────────────────── */}
      <section className="snap-section">
        <AnimateIn delay={0.1}>
          <GlassCard variant="plain">
            <p
              style={{
                fontFamily: 'var(--font-heading)',
                color: 'var(--accent-secondary)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                marginBottom: 'var(--space-4)',
              }}
            >
              Schrijven
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-2xl)',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: 'var(--space-10)',
              }}
            >
              Laatste posts
            </h2>

            <StaggerChildren style={{ display: 'flex', flexDirection: 'column' }}>
              {latestPosts.map((post, i) => (
                <motion.article
                  key={post.title}
                  whileHover={{ x: 4 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                  style={{
                    paddingBottom: 'var(--space-8)',
                    marginBottom: i < latestPosts.length - 1 ? 'var(--space-8)' : 0,
                    borderBottom: i < latestPosts.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                  }}
                >
                  <a href={post.href} style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
                    <div
                      style={{
                        display: 'flex',
                        gap: 'var(--space-3)',
                        alignItems: 'center',
                        marginBottom: 'var(--space-2)',
                      }}
                    >
                      <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {post.date}
                      </span>
                      <span style={{ color: 'var(--border-default)', userSelect: 'none' }}>·</span>
                      <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {post.readTime}
                      </span>
                    </div>
                    <h3
                      style={{
                        fontFamily: 'var(--font-heading)',
                        fontSize: 'var(--text-lg)',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        marginBottom: 'var(--space-2)',
                        transition: 'color var(--transition-fast)',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
                      onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
                    >
                      {post.title}
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.7, marginBottom: 0 }}>
                      {post.preview}
                    </p>
                  </a>
                </motion.article>
              ))}
            </StaggerChildren>

            <a
              href="/blog"
              style={{
                marginTop: 'var(--space-10)',
                display: 'inline-flex',
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--accent-secondary)'; }}
            >
              Alle posts →
            </a>
          </GlassCard>
        </AnimateIn>
      </section>

    </div>
  );
}
