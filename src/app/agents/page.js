'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';

const agents = [
  {
    id: 'code-auditor',
    name: 'Code Auditor',
    cli: 'code_auditor',
    description:
      'A 5-phase system that safely analyzes your codebase, identifies unused code, and generates actionable cleanup reports — without touching a single file until you say so.',
    status: 'Phase 1 Live',
    statusStyle: {
      bg: 'rgba(34,197,94,0.10)',
      border: 'rgba(34,197,94,0.25)',
      text: 'rgba(34,197,94,0.9)',
      dot: 'rgba(34,197,94,0.9)',
    },
    tags: ['Python', 'AST Analysis', 'Dependency Mapping', 'JSON Reports'],
    phases: [
      { label: 'Phase 1 — Discovery', status: '✅ Live', detail: 'Scans all .py, .js, .ts, .tsx files. Builds a complete import/export dependency map and detects circular dependencies. 100% read-only.' },
      { label: 'Phase 2 — Detection', status: '🔜 Coming', detail: 'Cross-references the dependency map against entry points to find code imported nowhere — unused exports, orphan files, dead variables.' },
      { label: 'Phase 3 — Verification', status: '🔜 Coming', detail: 'Safety check before any removal: re-examines flagged items with additional heuristics to eliminate false positives.' },
      { label: 'Phase 4 — Reporting', status: '🔜 Coming', detail: 'Generates HTML dashboard, CSV export, and JSON summary with per-file recommendations and risk assessments.' },
      { label: 'Phase 5 — Execution', status: '🔜 Coming', detail: 'Staged, reversible removal of confirmed dead code. Every change is committed atomically with a rollback path.' },
    ],
    commands: [
      { label: 'Discover (Phase 1)', cmd: 'python -m agents.code_auditor.cli discover --project . --verbose' },
      { label: 'Analyze report', cmd: 'python -m agents.code_auditor.cli analyze audit_report.json' },
      { label: 'Detect unused (Phase 2)', cmd: 'python -m agents.code_auditor.cli detect --report audit_report.json' },
      { label: 'Verify safety (Phase 3)', cmd: 'python -m agents.code_auditor.cli verify --report phase2_findings.json' },
    ],
  },
  {
    id: 'code-fixer',
    name: 'Code Fixer',
    cli: 'code_fixer',
    description:
      'Consumes verified audit findings, batches removals by risk level, runs your test suite after each batch, and commits atomically — with a rollback path if tests fail.',
    status: 'In ontwikkeling',
    statusStyle: {
      bg: 'rgba(232,185,49,0.10)',
      border: 'rgba(232,185,49,0.25)',
      text: 'var(--accent-secondary)',
      dot: 'var(--accent-primary)',
    },
    tags: ['Python', 'Git Integration', 'Batch Execution', 'HTML Reports'],
    phases: [
      { label: 'Analyze', status: '', detail: 'Reads phase3_verified.json and categorizes findings by type and risk. Shows a summary before any changes are made.' },
      { label: 'Plan', status: '', detail: 'Groups findings into batches of configurable size, ordering by risk level (low → high). Dry-run mode shows exactly what will change.' },
      { label: 'Fix', status: '', detail: 'Invokes the Code Auditor\'s Phase 5 executor per batch. Tests run after each batch. On failure, the batch is rolled back automatically.' },
      { label: 'Report', status: '', detail: 'Generates an HTML dashboard and JSON summary: batches attempted, lines removed, commits made, items needing manual review.' },
    ],
    commands: [
      { label: 'Dry run (plan only)', cmd: 'python agents/code_fixer/cli.py plan --report phase3_verified.json' },
      { label: 'Run full fix', cmd: 'python agents/code_fixer/cli.py fix --report phase3_verified.json' },
      { label: 'Verify specific items', cmd: 'python agents/code_fixer/cli.py verify --report phase3_verified.json --items U001 U002' },
      { label: 'Session status', cmd: 'python agents/code_fixer/cli.py status' },
    ],
  },
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    cli: 'orchestrator',
    description:
      'The coordination layer — an event-driven framework that routes CLI commands to registered agents, passes context between them (audit results → fixer), and logs every action.',
    status: 'Live',
    statusStyle: {
      bg: 'rgba(232,185,49,0.10)',
      border: 'rgba(232,185,49,0.25)',
      text: 'var(--accent-secondary)',
      dot: 'var(--accent-primary)',
    },
    tags: ['Python', 'Event Bus', 'Agent Registry', 'State Store'],
    phases: [
      { label: 'EventBus', status: '', detail: 'Synchronous pub/sub system. Agents publish events (AuditCompleted, FixFailed). The logger and other agents subscribe. Wildcard (*) subscriptions catch everything.' },
      { label: 'AgentRegistry', status: '', detail: 'Maps agent names to classes. Register once at startup, instantiate on demand. Adding a new agent is one line.' },
      { label: 'StateStore', status: '', detail: 'JSON-backed key-value store that persists between commands. After "audit", the fixer automatically reads the last audit result — no file-passing needed.' },
      { label: 'OrchestratorLogger', status: '', detail: 'Subscribes to all events. Prints ✓/✗ lines to terminal (verbose mode shows payloads). Appends every event to a JSON log file for auditing.' },
    ],
    commands: [
      { label: 'List agents', cmd: 'python main.py list' },
      { label: 'Audit a directory', cmd: 'python main.py audit ./src --verbose' },
      { label: 'Fix (auto-reads last audit)', cmd: 'python main.py fix' },
      { label: 'Fix explicit target', cmd: 'python main.py fix ./src' },
    ],
  },
];

function AgentCard({ agent }) {
  const [open, setOpen] = useState(false);

  return (
    <motion.article
      whileHover={{ borderLeftColor: 'var(--accent-primary)', backgroundColor: 'rgba(232,185,49,0.02)' }}
      transition={{ duration: 0.15 }}
      style={{
        border: '1px solid rgba(232,185,49,0.1)',
        borderLeft: `2px solid ${open ? 'var(--accent-primary)' : 'rgba(232,185,49,0.2)'}`,
        transition: 'border-left-color var(--transition-fast), background-color var(--transition-fast)',
      }}
    >
      {/* Card header — always visible */}
      <div style={{ padding: 'var(--space-8)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em', margin: 0 }}>
              {agent.name}
            </h2>
            <span style={{
              flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
              padding: '0.25rem var(--space-3)',
              fontSize: 'var(--text-xs)', fontFamily: 'var(--font-heading)', fontWeight: 600,
              backgroundColor: agent.statusStyle.bg, color: agent.statusStyle.text,
              border: `1px solid ${agent.statusStyle.border}`,
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: agent.statusStyle.dot, display: 'inline-block' }} />
              {agent.status}
            </span>
          </div>

          {/* Toggle button */}
          <button
            onClick={() => setOpen(v => !v)}
            style={{
              flexShrink: 0,
              background: 'none',
              border: '1px solid rgba(232,185,49,0.2)',
              color: 'var(--accent-secondary)',
              fontFamily: 'monospace',
              fontSize: 'var(--text-xs)',
              padding: '0.3rem var(--space-3)',
              cursor: 'pointer',
              letterSpacing: '0.08em',
              transition: 'border-color var(--transition-fast), color var(--transition-fast)',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.color = 'var(--accent-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(232,185,49,0.2)'; e.currentTarget.style.color = 'var(--accent-secondary)'; }}
          >
            {open ? '[ COLLAPSE ]' : '[ MANUAL ]'}
          </button>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.75, marginBottom: 'var(--space-5)' }}>
          {agent.description}
        </p>

        {/* CLI name label */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
          <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            AGENT ID
          </span>
          <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', backgroundColor: 'rgba(232,185,49,0.05)', padding: '0.15rem var(--space-2)', border: '1px solid rgba(232,185,49,0.12)' }}>
            {agent.cli}
          </span>
        </div>

        {/* Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
          {agent.tags.map(tag => (
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
      </div>

      {/* Expandable manual section */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="manual"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              padding: 'var(--space-8)',
              paddingTop: 0,
              borderTop: '1px solid rgba(232,185,49,0.08)',
            }}>
              {/* Phases / Components */}
              <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
                {agent.id === 'orchestrator' ? 'COMPONENTS' : 'PHASES'}
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginBottom: 'var(--space-8)' }}>
                {agent.phases.map((phase, i) => (
                  <div key={i} style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
                    <span style={{ width: 14, height: 1, backgroundColor: 'var(--accent-primary)', flexShrink: 0, marginTop: '0.6rem' }} />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-1)' }}>
                        <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {phase.label}
                        </span>
                        {phase.status && (
                          <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)' }}>
                            {phase.status}
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
                        {phase.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Commands */}
              <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
                COMMANDS
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {agent.commands.map((c, i) => (
                  <div key={i}>
                    <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em', display: 'block', marginBottom: 'var(--space-1)' }}>
                      # {c.label}
                    </span>
                    <div style={{
                      fontFamily: 'monospace',
                      fontSize: 'var(--text-sm)',
                      color: 'var(--accent-secondary)',
                      backgroundColor: 'rgba(232,185,49,0.04)',
                      border: '1px solid rgba(232,185,49,0.1)',
                      padding: 'var(--space-3) var(--space-4)',
                      wordBreak: 'break-all',
                    }}>
                      <span style={{ color: 'var(--accent-primary)', userSelect: 'none' }}>$ </span>
                      {c.cmd}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

export default function AgentsPage() {
  return (
    <section style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 'var(--space-20) var(--space-6)' }}>
      <div style={{ width: '100%', maxWidth: '900px', margin: '0 auto' }}>

        <AnimateIn delay={0.05}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-4)' }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)', boxShadow: '0 0 8px rgba(232,185,49,0.7)' }} />
            <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--accent-secondary)' }}>
              SYS.INDEX // AGENTS
            </span>
          </div>
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>AI</div>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)' }}>AGENTS.</div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.7, maxWidth: '580px', marginBottom: 'var(--space-16)' }}>
            Specialized agents that audit, fix, and coordinate — built on a shared event-driven framework. Click <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)' }}>[ MANUAL ]</span> to expand commands and documentation.
          </p>
        </AnimateIn>

        <StaggerChildren style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {agents.map(agent => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </StaggerChildren>

      </div>
    </section>
  );
}
