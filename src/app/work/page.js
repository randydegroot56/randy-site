'use client';

import { motion } from 'framer-motion';
import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';

/* ── Data ────────────────────────────────────────────────────── */

const projects = [
  {
    title: 'RAG Chatbot',
    description:
      'Een intelligente chatbot die PDF documenten doorzoekt met vector embeddings. Upload een PDF, stel vragen, en krijg antwoorden gebaseerd op de inhoud — inclusief bronverwijzingen.',
    tags: ['Python', 'LangChain', 'ChromaDB', 'Streamlit', 'OpenAI Embeddings'],
    status: 'Afgerond',
    statusStyle: {
      bg: 'rgba(34, 197, 94, 0.12)',
      border: 'rgba(34, 197, 94, 0.28)',
      text: 'rgba(34, 197, 94, 0.95)',
      dot: 'rgba(34, 197, 94, 0.9)',
    },
    features: [
      'Hybrid search (semantic + keyword)',
      'Conversation memory',
      'Contextual chunk prefixes',
    ],
  },
  {
    title: 'Personal Command Center',
    description:
      'Een persoonlijk dashboard dat AI-gegenereerde briefings combineert met weer, taken, en nieuws. Ontworpen als dagelijks startpunt met real-time data.',
    tags: ['React', 'Vite', 'FastAPI', 'Claude API', 'Python'],
    status: 'In ontwikkeling',
    statusStyle: {
      bg: 'rgba(232, 185, 49, 0.12)',
      border: 'rgba(232, 185, 49, 0.30)',
      text: 'var(--accent-secondary)',
      dot: 'var(--accent-primary)',
    },
    features: [
      'AI-generated daily briefings',
      'Weather integration',
      'Task management',
    ],
  },
  {
    title: 'randy.dev',
    description:
      'Deze website — gebouwd van scratch met Next.js. Custom theming systeem, Framer Motion animaties, en een generatief netwerk achtergrondpatroon met 3D scroll-rotatie.',
    tags: ['Next.js', 'React', 'Framer Motion', 'CSS Variables', 'Canvas API'],
    status: 'Live',
    statusStyle: {
      bg: 'rgba(232, 185, 49, 0.12)',
      border: 'rgba(232, 185, 49, 0.30)',
      text: 'var(--accent-secondary)',
      dot: 'var(--accent-primary)',
    },
    features: [
      'Custom Honey & smoke theme',
      'Dark/light mode',
      'Scroll-snap navigatie',
    ],
  },
];

/* ── Page ─────────────────────────────────────────────────────── */

export default function WorkPage() {
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
      <div style={{ width: '100%', maxWidth: '900px', margin: '0 auto' }}>

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
            Portfolio
          </p>
          <h1
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: 'var(--text-3xl)',
              color: 'var(--text-primary)',
              marginBottom: 'var(--space-4)',
            }}
          >
            Mijn werk
          </h1>
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: 'var(--text-md)',
              lineHeight: 1.7,
              maxWidth: '580px',
              marginBottom: 'var(--space-16)',
            }}
          >
            Een selectie van projecten waar ik aan heb gewerkt — van AI-gedreven tools
            tot full-stack applicaties.
          </p>
        </AnimateIn>

        {/* Project cards */}
        <StaggerChildren
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}
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
                padding: 'var(--space-8)',
                border: '1px solid var(--border-subtle)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              {/* Title + status badge */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: 'var(--space-4)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                <h2
                  style={{
                    fontFamily: 'var(--font-heading)',
                    fontSize: 'var(--text-xl)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {project.title}
                </h2>
                <span
                  style={{
                    flexShrink: 0,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 'var(--space-1)',
                    padding: '0.25rem var(--space-3)',
                    borderRadius: 'var(--radius-full)',
                    fontSize: 'var(--text-xs)',
                    fontFamily: 'var(--font-heading)',
                    fontWeight: 600,
                    backgroundColor: project.statusStyle.bg,
                    color: project.statusStyle.text,
                    border: `1px solid ${project.statusStyle.border}`,
                  }}
                >
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: project.statusStyle.dot,
                      display: 'inline-block',
                    }}
                  />
                  {project.status}
                </span>
              </div>

              {/* Description */}
              <p
                style={{
                  color: 'var(--text-secondary)',
                  fontSize: 'var(--text-sm)',
                  lineHeight: 1.75,
                  marginBottom: 'var(--space-6)',
                }}
              >
                {project.description}
              </p>

              {/* Features */}
              <ul
                style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: `0 0 var(--space-6)`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-2)',
                }}
              >
                {project.features.map(f => (
                  <li
                    key={f}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-3)',
                      color: 'var(--text-secondary)',
                      fontSize: 'var(--text-sm)',
                    }}
                  >
                    <span
                      style={{
                        width: 14,
                        height: 2,
                        backgroundColor: 'var(--accent-primary)',
                        borderRadius: 2,
                        flexShrink: 0,
                      }}
                    />
                    {f}
                  </li>
                ))}
              </ul>

              {/* Tags */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                {project.tags.map(tag => (
                  <span
                    key={tag}
                    style={{
                      padding: '0.2rem var(--space-3)',
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
      </div>
    </section>
  );
}
