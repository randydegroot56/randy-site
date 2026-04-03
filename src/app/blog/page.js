'use client';

import { motion } from 'framer-motion';
import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';

/* ── Data ────────────────────────────────────────────────────── */

const posts = [
  {
    date: '28 maart 2026',
    readTime: '8 min',
    title: 'Hoe ik mijn eerste RAG chatbot bouwde',
    preview:
      'Van PDF naar antwoord — een deep dive in embeddings, vector databases, en waarom context alles is.',
    href: '#',
  },
  {
    date: '15 maart 2026',
    readTime: '5 min',
    title: 'Claude Code als development partner',
    preview:
      'Mijn ervaringen met AI-assisted coding: wat werkt, wat niet, en hoe je het beste uit Claude Code haalt.',
    href: '#',
  },
  {
    date: '2 maart 2026',
    readTime: '6 min',
    title: 'Van nul naar Next.js: mijn website bouwen',
    preview:
      'Waarom ik koos voor Next.js, hoe ik een custom theming systeem opzette, en lessen geleerd onderweg.',
    href: '#',
  },
];

/* ── Page ─────────────────────────────────────────────────────── */

export default function BlogPage() {
  return (
    <section
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: 'var(--space-20) var(--space-6)',
      }}
    >
      <div style={{ width: '100%', maxWidth: '720px', margin: '0 auto' }}>

        {/* Header */}
        <AnimateIn delay={0.05}>
          <p
            style={{
              fontFamily: 'var(--font-heading)',
              color: 'var(--accent-secondary)',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              marginBottom: 'var(--space-2)',
            }}
          >
            Schrijven
          </p>
          <h1
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: 'var(--text-3xl)',
              color: 'var(--text-primary)',
              marginBottom: 'var(--space-4)',
            }}
          >
            Blog
          </h1>
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: 'var(--text-md)',
              lineHeight: 1.7,
              marginBottom: 'var(--space-16)',
            }}
          >
            Gedachten over development, AI, en wat ik onderweg leer.
          </p>
        </AnimateIn>

        {/* Post list */}
        <StaggerChildren style={{ display: 'flex', flexDirection: 'column' }}>
          {posts.map((post, i) => (
            <motion.article
              key={post.title}
              whileHover={{ backgroundColor: 'var(--bg-secondary)' }}
              transition={{ duration: 0.15 }}
              style={{
                padding: 'var(--space-8) var(--space-4)',
                borderRadius: 'var(--radius-md)',
                borderBottom: i < posts.length - 1 ? '1px solid var(--border-subtle)' : 'none',
              }}
            >
              <a href={post.href} style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
                {/* Meta */}
                <div
                  style={{
                    display: 'flex',
                    gap: 'var(--space-3)',
                    alignItems: 'center',
                    marginBottom: 'var(--space-3)',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-muted)',
                    }}
                  >
                    {post.date}
                  </span>
                  <span style={{ color: 'var(--border-default)', userSelect: 'none' }}>·</span>
                  <span
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-muted)',
                    }}
                  >
                    {post.readTime} leestijd
                  </span>
                </div>

                {/* Title */}
                <h2
                  style={{
                    fontFamily: 'var(--font-heading)',
                    fontSize: 'var(--text-xl)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    marginBottom: 'var(--space-3)',
                    transition: 'color var(--transition-fast)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
                >
                  {post.title}
                </h2>

                {/* Preview */}
                <p
                  style={{
                    color: 'var(--text-secondary)',
                    fontSize: 'var(--text-base)',
                    lineHeight: 1.7,
                    marginBottom: 'var(--space-4)',
                  }}
                >
                  {post.preview}
                </p>

                {/* CTA */}
                <span
                  style={{
                    fontFamily: 'var(--font-heading)',
                    fontSize: 'var(--text-sm)',
                    fontWeight: 500,
                    color: 'var(--accent-secondary)',
                  }}
                >
                  Lees meer →
                </span>
              </a>
            </motion.article>
          ))}
        </StaggerChildren>
      </div>
    </section>
  );
}
