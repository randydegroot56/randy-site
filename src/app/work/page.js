'use client';

import { motion } from 'framer-motion';
import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';

const projects = [
  {
    title: 'Property Document AI',
    description: 'AI-powered document analysis for real estate professionals. Upload lease contracts, valuation reports, or due diligence packages — ask questions, get cited answers from the source material.',
    tags: ['Python', 'LangChain', 'ChromaDB', 'Streamlit', 'OpenAI Embeddings'],
    status: 'Afgerond',
    statusStyle: { bg: 'rgba(34,197,94,0.10)', border: 'rgba(34,197,94,0.25)', text: 'rgba(34,197,94,0.9)', dot: 'rgba(34,197,94,0.9)' },
    features: ['Hybrid search (semantic + keyword)', 'Conversation memory', 'Source citations per answer'],
  },
  {
    title: 'RE Intelligence Dashboard',
    description: 'A real estate intelligence hub that aggregates market data, generates AI briefings, and surfaces actionable insights for property professionals. Designed as a daily command center.',
    tags: ['React', 'Vite', 'FastAPI', 'Claude API', 'Python'],
    status: 'In ontwikkeling',
    statusStyle: { bg: 'rgba(232,185,49,0.10)', border: 'rgba(232,185,49,0.25)', text: 'var(--accent-secondary)', dot: 'var(--accent-primary)' },
    features: ['AI-generated market briefings', 'Data aggregation pipeline', 'Custom alert rules'],
  },
  {
    title: 'Automated Valuation Model',
    description: 'A machine learning pipeline that estimates property values using transaction data, location features, and market trends. Built on Dutch housing market data.',
    tags: ['Python', 'scikit-learn', 'pandas', 'FastAPI'],
    status: 'Concept',
    statusStyle: { bg: 'rgba(232,185,49,0.08)', border: 'rgba(232,185,49,0.2)', text: 'var(--accent-secondary)', dot: 'var(--accent-primary)' },
    features: ['Feature engineering pipeline', 'REST API endpoint', 'Confidence intervals'],
  },
  {
    title: 'randy.dev',
    description: 'This site — built from scratch with Next.js. Gold line-art Rotterdam skyline, layered parallax backgrounds, bold editorial redesign, and Framer Motion animations throughout.',
    tags: ['Next.js', 'React', 'Framer Motion', 'CSS Variables', 'Canvas API'],
    status: 'Live',
    statusStyle: { bg: 'rgba(232,185,49,0.10)', border: 'rgba(232,185,49,0.25)', text: 'var(--accent-secondary)', dot: 'var(--accent-primary)' },
    features: ['Rotterdam SVG draw-in animation', '3-layer parallax background', 'Dark-first editorial design'],
  },
];

export default function WorkPage() {
  return (
    <section style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 'var(--space-20) var(--space-6)' }}>
      <div style={{ width: '100%', maxWidth: '900px', margin: '0 auto' }}>

        <AnimateIn delay={0.05}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-4)' }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)', boxShadow: '0 0 8px rgba(232,185,49,0.7)' }} />
            <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--accent-secondary)' }}>
              SYS.INDEX // PROJECTS
            </span>
          </div>
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>BUILT</div>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>PROJECTS.</div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.7, maxWidth: '580px', marginBottom: 'var(--space-16)' }}>
            AI automation tools for the real estate sector — from document intelligence to market analysis.
          </p>
        </AnimateIn>

        <StaggerChildren style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {projects.map(project => (
            <motion.article
              key={project.title}
              whileHover={{ borderLeftColor: 'var(--accent-primary)', backgroundColor: 'rgba(232,185,49,0.02)' }}
              transition={{ duration: 0.15 }}
              style={{
                padding: 'var(--space-8)',
                border: '1px solid rgba(232,185,49,0.1)',
                borderLeft: '2px solid rgba(232,185,49,0.2)',
                boxShadow: 'none',
                transition: 'border-left-color var(--transition-fast), background-color var(--transition-fast)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                  {project.title}
                </h2>
                <span style={{
                  flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
                  padding: '0.25rem var(--space-3)',
                  fontSize: 'var(--text-xs)', fontFamily: 'var(--font-heading)', fontWeight: 600,
                  backgroundColor: project.statusStyle.bg, color: project.statusStyle.text,
                  border: `1px solid ${project.statusStyle.border}`,
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: project.statusStyle.dot, display: 'inline-block' }} />
                  {project.status}
                </span>
              </div>

              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.75, marginBottom: 'var(--space-5)' }}>
                {project.description}
              </p>

              <ul style={{ listStyle: 'none', padding: 0, margin: `0 0 var(--space-5)`, display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {project.features.map(f => (
                  <li key={f} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                    <span style={{ width: 14, height: 1, backgroundColor: 'var(--accent-primary)', flexShrink: 0 }} />
                    {f}
                  </li>
                ))}
              </ul>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                {project.tags.map(tag => (
                  <span key={tag} style={{
                    padding: '0.2rem var(--space-3)',
                    fontSize: 'var(--text-xs)', fontFamily: 'var(--font-heading)', fontWeight: 500,
                    color: 'var(--text-muted)',
                    backgroundColor: 'rgba(232,185,49,0.04)',
                    border: '1px solid rgba(232,185,49,0.1)',
                  }}>
                    {tag}
                  </span>
                ))}
              </div>
            </motion.article>
          ))}
        </StaggerChildren>
      </div>
    </section>
  );
}
