'use client';

import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';
import GlassCard from '../../components/GlassCard';

const posts = [
  {
    date: '28 maart 2026',
    readTime: '8 min',
    title: 'Building a Document AI for Dutch Lease Contracts',
    preview: 'How I built a RAG pipeline that lets property managers ask questions across hundreds of pages of lease contracts — and actually get cited answers.',
    href: '#',
  },
  {
    date: '15 maart 2026',
    readTime: '6 min',
    title: 'How AI is Changing Property Valuation in the Netherlands',
    preview: 'Automated Valuation Models, data availability, and why the Dutch market is both challenging and exciting for AI-based pricing tools.',
    href: '#',
  },
  {
    date: '2 maart 2026',
    readTime: '5 min',
    title: 'Claude Code as a PropTech Build Partner',
    preview: 'Using AI-assisted coding to build real estate automation tools faster — what works, what breaks, and how to stay in control of the output.',
    href: '#',
  },
];

export default function BlogPage() {
  return (
    <section style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 'var(--space-20) var(--space-6)' }}>
      <div style={{ width: '100%', maxWidth: '720px', margin: '0 auto' }}>

        <AnimateIn delay={0.05}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-4)' }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)', boxShadow: '0 0 8px rgba(232,185,49,0.7)' }} />
            <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--accent-secondary)' }}>
              LOG // WRITING
            </span>
          </div>
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>FIELD</div>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>NOTES.</div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.7, marginBottom: 'var(--space-16)' }}>
            AI, real estate data, and what I learn building at the intersection of both.
          </p>
        </AnimateIn>

        <StaggerChildren style={{ display: 'flex', flexDirection: 'column' }}>
          {posts.map((post, i) => (
            <GlassCard key={post.title} style={{ marginBottom: i < posts.length - 1 ? 'var(--space-4)' : 0 }}>
              <div style={{ padding: 'var(--space-8) var(--space-4)' }}>
                <a href={post.href} style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
                  <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                    <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>{post.date}</span>
                    <span style={{ color: 'rgba(232,185,49,0.2)' }}>·</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>{post.readTime} read</span>
                  </div>
                  <h2
                    style={{
                      fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xl)', fontWeight: 700,
                      color: 'var(--text-primary)', letterSpacing: '-0.01em',
                      marginBottom: 'var(--space-3)', lineHeight: 1.2,
                      transition: 'color var(--transition-fast)',
                    }}
                  >
                    {post.title}
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.7, margin: 0 }}>
                    {post.preview}
                  </p>
                </a>
              </div>
            </GlassCard>
          ))}
        </StaggerChildren>
      </div>
    </section>
  );
}
