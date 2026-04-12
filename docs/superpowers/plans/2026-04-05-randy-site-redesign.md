# Randy.dev PropTech Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign randy.dev into a professional PropTech / Real Estate AI Automation portfolio with bold editorial aesthetics, a gold line-art Rotterdam skyline background, layered parallax, and AI/tech-toned copy throughout.

**Architecture:** Three new fixed background layers (DataGrid → CityskylineBackground → existing NetworkBackground) are mounted globally in layout.js. The homepage is fully rewritten — GlassCard removed, replaced with 5 bold editorial scroll-snap sections. Inner pages (/work, /about, /blog) get editorial headers and repositioned content.

**Tech Stack:** Next.js 14.2, React 18, Framer Motion 12, SVG stroke-dashoffset animation via Framer Motion `pathLength`, inline style objects with CSS variables (no CSS framework).

**Spec:** `docs/superpowers/specs/2026-04-05-randy-site-redesign.md`

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `src/components/DataGrid.tsx` | Subtle CSS grid background, slowest parallax (0.05×) |
| Create | `src/components/CityskylineBackground.tsx` | Gold Rotterdam SVG skyline, draw-in animation, mid parallax (0.15×) |
| Modify | `src/app/layout.js` | Mount DataGrid + CityskylineBackground, adjust z-index stack |
| Modify | `src/components/Navbar.jsx` | Logo → RDG., uppercase nav links, CONTACT gold button |
| Modify | `src/components/Footer.jsx` | Match editorial style, update copy |
| Rewrite | `src/app/page.js` | 5-section homepage, no GlassCard, bold editorial layout |
| Rewrite | `src/app/work/page.js` | Editorial header, new RE-focused project content |
| Rewrite | `src/app/about/page.js` | Repositioned PropTech bio, new stack |
| Rewrite | `src/app/blog/page.js` | New RE/AI blog post content |

---

## Task 1: DataGrid Background Component

**Files:**
- Create: `src/components/DataGrid.tsx`

- [ ] **Step 1: Create the component**

```tsx
'use client';

import { useScroll, useTransform, motion } from 'framer-motion';

export default function DataGrid() {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 3000], [0, -150]);

  return (
    <motion.div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1,
        pointerEvents: 'none',
        y,
        backgroundImage: `
          linear-gradient(rgba(232,185,49,0.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(232,185,49,0.025) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
      }}
    >
      {/* Corner coordinate labels */}
      <span style={{
        position: 'absolute',
        top: 12,
        left: 16,
        fontFamily: 'monospace',
        fontSize: '10px',
        color: 'rgba(232,185,49,0.15)',
        letterSpacing: '0.05em',
        userSelect: 'none',
      }}>
        51.9225°N / 4.4792°E
      </span>
      <span style={{
        position: 'absolute',
        top: 12,
        right: 16,
        fontFamily: 'monospace',
        fontSize: '10px',
        color: 'rgba(232,185,49,0.15)',
        letterSpacing: '0.05em',
        userSelect: 'none',
      }}>
        NL.RE.GRID_v1
      </span>
      <span style={{
        position: 'absolute',
        bottom: 12,
        left: 16,
        fontFamily: 'monospace',
        fontSize: '10px',
        color: 'rgba(232,185,49,0.1)',
        letterSpacing: '0.05em',
        userSelect: 'none',
      }}>
        AMS / RTD / UTR
      </span>
    </motion.div>
  );
}
```

- [ ] **Step 2: Verify no TypeScript errors**

Run: `npm run build`
Expected: Compiles without errors. (We'll integrate it in Task 3 — for now just confirm the file is valid.)

---

## Task 2: CityskylineBackground Component

**Files:**
- Create: `src/components/CityskylineBackground.tsx`

This component renders a full-width gold line-art Rotterdam skyline (inspired by the Erasmus Bridge + Euromast + city buildings). It draws itself in on page load using Framer Motion's `pathLength` animation, then parallaxes slowly upward as the user scrolls.

- [ ] **Step 1: Create the component**

```tsx
'use client';

import { useScroll, useTransform, motion } from 'framer-motion';

const DRAW_DURATION = 2.5;

// Each path group draws in at a different delay for a staggered reveal
function pathAnim(delay: number) {
  return {
    hidden: { pathLength: 0, opacity: 0 },
    visible: {
      pathLength: 1,
      opacity: 1,
      transition: { pathLength: { duration: DRAW_DURATION, delay, ease: 'easeInOut' }, opacity: { duration: 0.3, delay } },
    },
  } as const;
}

export default function CityskylineBackground() {
  const { scrollY } = useScroll();
  // Skyline moves up at 0.15× scroll speed
  const y = useTransform(scrollY, [0, 3000], [0, -450]);

  return (
    <motion.div
      aria-hidden="true"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 2,
        pointerEvents: 'none',
        y,
        opacity: 0.32,
      }}
    >
      <svg
        viewBox="0 0 1440 300"
        preserveAspectRatio="xMidYMax meet"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', display: 'block' }}
      >
        {/* ── Ground line ──────────────────────────────── */}
        <motion.line
          x1="0" y1="292" x2="1440" y2="292"
          stroke="rgba(232,185,49,0.5)"
          strokeWidth="1"
          variants={pathAnim(0)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Left buildings cluster ───────────────────── */}
        <motion.path
          d="M 0,292 L 0,240 L 38,240 L 38,225 L 55,225 L 55,210 L 68,210 L 68,198 L 83,198 L 83,185 L 98,185 L 98,172 L 112,172 L 112,158 L 128,158 L 128,144 L 148,144 L 148,130 L 168,130 L 168,118 L 190,118 L 190,130 L 208,130 L 208,118 L 228,118 L 228,130 L 242,130 L 242,118 L 258,118 L 258,132 L 272,132 L 272,145 L 290,145 L 290,158 L 308,158 L 308,170 L 326,170 L 326,182 L 345,182 L 345,195 L 365,195 L 365,210 L 380,210"
          fill="none"
          stroke="rgba(232,185,49,0.75)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(0.1)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Bridge approach ramps ─────────────────────── */}
        <motion.path
          d="M 378,228 L 665,228"
          fill="none"
          stroke="rgba(232,185,49,0.8)"
          strokeWidth="2"
          variants={pathAnim(0.35)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Erasmus Bridge pylon (main shaft, leans left) */}
        <motion.path
          d="M 464,228 L 448,38"
          fill="none"
          stroke="#E8B931"
          strokeWidth="2.5"
          strokeLinecap="round"
          variants={pathAnim(0.5)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Pylon A-frame right support leg ──────────── */}
        <motion.path
          d="M 448,38 L 470,148"
          fill="none"
          stroke="rgba(232,185,49,0.9)"
          strokeWidth="2"
          strokeLinecap="round"
          variants={pathAnim(0.7)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Bridge cables — left side (5 cables) ─────── */}
        <motion.path
          d="M 448,38 L 382,226 M 448,38 L 402,226 M 448,38 L 420,226 M 448,38 L 438,226 M 448,38 L 455,226"
          fill="none"
          stroke="rgba(232,185,49,0.5)"
          strokeWidth="1"
          variants={pathAnim(0.85)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Bridge cables — right side (10 cables) ───── */}
        <motion.path
          d="M 448,38 L 478,226 M 448,38 L 500,226 M 448,38 L 522,226 M 448,38 L 544,226 M 448,38 L 565,226 M 448,38 L 586,226 M 448,38 L 607,226 M 448,38 L 628,226 M 448,38 L 648,226 M 448,38 L 663,226"
          fill="none"
          stroke="rgba(232,185,49,0.45)"
          strokeWidth="1"
          variants={pathAnim(0.95)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Centre buildings (between bridge & Euromast) */}
        <motion.path
          d="M 665,228 L 665,195 L 690,195 L 690,180 L 712,180 L 712,165 L 732,165 L 732,155 L 752,155 L 752,162 L 772,162 L 772,172 L 792,172 L 792,182 L 810,182"
          fill="none"
          stroke="rgba(232,185,49,0.7)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(1.25)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Euromast shaft ────────────────────────────── */}
        <motion.path
          d="M 822,292 L 822,15"
          fill="none"
          stroke="rgba(232,185,49,0.9)"
          strokeWidth="1.8"
          strokeLinecap="round"
          variants={pathAnim(1.45)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Euromast observation disc ─────────────────── */}
        <motion.path
          d="M 806,105 L 838,105 L 838,122 L 806,122 Z M 814,105 L 814,95 L 830,95 L 830,105"
          fill="none"
          stroke="rgba(232,185,49,0.85)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(1.6)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Euromast tip dot ──────────────────────────── */}
        <motion.circle
          cx="822" cy="15" r="3"
          fill="#E8B931"
          variants={{
            hidden: { opacity: 0, scale: 0 },
            visible: { opacity: 1, scale: 1, transition: { duration: 0.4, delay: 1.8 } },
          }}
          initial="hidden"
          animate="visible"
        />

        {/* ── Right buildings cluster ───────────────────── */}
        <motion.path
          d="M 838,292 L 838,192 L 862,192 L 862,175 L 885,175 L 885,160 L 908,160 L 908,148 L 932,148 L 932,158 L 952,158 L 952,170 L 972,170 L 972,182 L 995,182 L 995,195 L 1020,195 L 1020,208 L 1050,208 L 1050,220 L 1085,220 L 1085,230 L 1125,230 L 1125,240 L 1170,240 L 1170,248 L 1222,248 L 1222,256 L 1285,256 L 1285,264 L 1355,264 L 1355,272 L 1440,272 L 1440,292"
          fill="none"
          stroke="rgba(232,185,49,0.65)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(1.75)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Stars ─────────────────────────────────────── */}
        <motion.g
          variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { duration: 1, delay: 2.2 } } }}
          initial="hidden"
          animate="visible"
        >
          {/* 4-point star (like in reference image) */}
          <path d="M 280,45 L 284,52 L 291,55 L 284,58 L 280,65 L 276,58 L 269,55 L 276,52 Z"
            fill="rgba(232,185,49,0.6)" />
          {/* Moon crescent */}
          <path d="M 1180,35 Q 1200,40 1200,58 Q 1200,76 1180,80 Q 1196,72 1196,58 Q 1196,44 1180,35 Z"
            fill="rgba(232,185,49,0.55)" />
          {/* Small dot stars */}
          <circle cx="120" cy="30" r="1.5" fill="rgba(232,185,49,0.4)" />
          <circle cx="600" cy="22" r="1.2" fill="rgba(232,185,49,0.35)" />
          <circle cx="950" cy="40" r="1.5" fill="rgba(232,185,49,0.3)" />
          <circle cx="1320" cy="28" r="1.2" fill="rgba(232,185,49,0.4)" />
        </motion.g>
      </svg>
    </motion.div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `npm run build`
Expected: Compiles without errors.

---

## Task 3: Update layout.js

**Files:**
- Modify: `src/app/layout.js`

Mount DataGrid and CityskylineBackground in the correct z-index order: DataGrid (z:1) → CityskylineBackground (z:2) → NetworkBackground (existing, z:3) → vignette (z:5) → content (z:6+).

- [ ] **Step 1: Replace layout.js**

```js
import '../styles/globals.css';
import { ThemeProvider } from '../components/ThemeProvider';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import PageTransition from '../components/PageTransition';
import NetworkBackground from '../components/NetworkBackground';
import CityskylineBackground from '../components/CityskylineBackground';
import DataGrid from '../components/DataGrid';

export const metadata = {
  title: 'RDG. — Real Estate AI Automation',
  description: 'Randy de Groot — I build AI tools that automate real estate workflows.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="dark">
      <body style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <ThemeProvider>
          {/* Layer 1: subtle data grid (slowest parallax) */}
          <DataGrid />

          {/* Layer 2: Rotterdam skyline SVG (mid parallax) */}
          <CityskylineBackground />

          {/* Layer 3: particle network canvas (existing, fastest) */}
          <NetworkBackground
            nodeColor="#E8B931"
            pulseColor="#C49A1A"
            bgColor="transparent"
          />

          {/* Vignette overlay — fades top/bottom edges into bg */}
          <div
            aria-hidden="true"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 5,
              pointerEvents: 'none',
              background: 'linear-gradient(to bottom, var(--bg-primary) 0%, transparent 12%, transparent 88%, var(--bg-primary) 100%)',
            }}
          />

          <Navbar />
          <main style={{ flex: 1, overflowX: 'hidden', position: 'relative', zIndex: 6 }}>
            <PageTransition>{children}</PageTransition>
          </main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
```

Note: `data-theme="dark"` is now the default since the design is dark-first. The ThemeProvider still respects localStorage and toggles work normally.

- [ ] **Step 2: Start dev server and verify three background layers are visible**

Run: `npm run dev`
Open: http://localhost:3000
Expected: Dark background with faint gold grid, Rotterdam skyline at the bottom drawing itself in over ~2.5s, gold particle network on top. Vignette fades top and bottom.

- [ ] **Step 3: Commit**

```bash
git add src/components/DataGrid.tsx src/components/CityskylineBackground.tsx src/app/layout.js
git commit -m "feat: add layered parallax backgrounds (DataGrid + Rotterdam skyline)"
```

---

## Task 4: Navbar Redesign

**Files:**
- Modify: `src/components/Navbar.jsx`

Changes: logo `randy.dev` → `RDG.` (monospace, gold), nav links get uppercase + letter-spacing treatment, add CONTACT button with gold border, mobile overlay gets same treatment.

- [ ] **Step 1: Replace Navbar.jsx**

```jsx
'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';

const NAV_LINKS = [
  { label: 'WORK',  href: '/work' },
  { label: 'ABOUT', href: '/about' },
  { label: 'BLOG',  href: '/blog' },
];

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [hoveredHref, setHoveredHref] = useState(null);

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  const isActive = href =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <>
      <style>{`
        .nav-desktop { display: flex; }
        .nav-hamburger { display: none; }
        @media (max-width: 767px) {
          .nav-desktop   { display: none; }
          .nav-hamburger { display: flex; }
        }
      `}</style>

      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          backgroundColor: 'color-mix(in srgb, var(--bg-primary) 85%, transparent)',
          borderBottom: '1px solid rgba(232,185,49,0.08)',
        }}
      >
        <div
          className="container"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '4rem' }}
        >
          {/* Logo */}
          <Link
            href="/"
            style={{
              fontFamily: 'monospace',
              fontWeight: 700,
              fontSize: 'var(--text-lg)',
              color: 'var(--accent-primary)',
              letterSpacing: '0.05em',
              textDecoration: 'none',
            }}
          >
            RDG<span style={{ color: 'rgba(232,185,49,0.4)' }}>.</span>
          </Link>

          {/* Desktop nav */}
          <nav className="nav-desktop" style={{ alignItems: 'center', gap: 'var(--space-8)' }}>
            <LayoutGroup>
              {NAV_LINKS.map(({ label, href }) => (
                <div
                  key={href}
                  style={{ position: 'relative' }}
                  onMouseEnter={() => setHoveredHref(href)}
                  onMouseLeave={() => setHoveredHref(null)}
                >
                  <Link
                    href={href}
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      letterSpacing: '0.12em',
                      color: isActive(href) || hoveredHref === href
                        ? 'var(--accent-primary)'
                        : 'var(--text-secondary)',
                      textDecoration: 'none',
                      display: 'block',
                      paddingBottom: 'var(--space-1)',
                      transition: 'color var(--transition-base)',
                    }}
                  >
                    {label}
                  </Link>

                  <AnimatePresence>
                    {hoveredHref === href && !isActive(href) && (
                      <motion.span
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        exit={{ scaleX: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        style={{
                          position: 'absolute', bottom: 0, left: 0, right: 0,
                          height: '1px', backgroundColor: 'var(--accent-primary)',
                          transformOrigin: 'left',
                        }}
                      />
                    )}
                  </AnimatePresence>

                  {isActive(href) && (
                    <motion.span
                      layoutId="nav-underline"
                      style={{
                        position: 'absolute', bottom: 0, left: 0, right: 0,
                        height: '1px', backgroundColor: 'var(--accent-primary)',
                      }}
                    />
                  )}
                </div>
              ))}
            </LayoutGroup>

            {/* Contact button */}
            <a
              href="mailto:hello@randy.dev"
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                padding: 'var(--space-2) var(--space-4)',
                border: '1px solid rgba(232,185,49,0.3)',
                transition: 'border-color var(--transition-fast), color var(--transition-fast)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                e.currentTarget.style.color = 'var(--accent-primary)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'rgba(232,185,49,0.3)';
                e.currentTarget.style.color = 'var(--accent-secondary)';
              }}
            >
              CONTACT
            </a>

            <ThemeToggle />
          </nav>

          {/* Mobile: ThemeToggle + hamburger */}
          <div className="nav-hamburger" style={{ alignItems: 'center', gap: 'var(--space-3)' }}>
            <ThemeToggle />
            <button
              aria-label={menuOpen ? 'Sluit menu' : 'Open menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(v => !v)}
              style={{
                width: '2.5rem', height: '2.5rem',
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: '5px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(232,185,49,0.2)',
                cursor: 'pointer', flexShrink: 0,
              }}
            >
              {[
                menuOpen ? 'translateY(7px) rotate(45deg)' : 'none',
                null,
                menuOpen ? 'translateY(-7px) rotate(-45deg)' : 'none',
              ].map((transform, i) => (
                <span
                  key={i}
                  style={{
                    display: 'block', width: '18px', height: '1px',
                    backgroundColor: 'var(--accent-primary)',
                    transition: 'transform var(--transition-base), opacity var(--transition-base)',
                    transform: transform || 'none',
                    opacity: i === 1 && menuOpen ? 0 : 1,
                  }}
                />
              ))}
            </button>
          </div>
        </div>
      </motion.header>

      {/* Mobile fullscreen overlay */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 99,
              backgroundColor: 'var(--bg-primary)',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              gap: 'var(--space-8)',
            }}
          >
            {NAV_LINKS.map(({ label, href }) => (
              <Link
                key={href}
                href={href}
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-2xl)',
                  fontWeight: 800,
                  letterSpacing: '0.06em',
                  color: isActive(href) ? 'var(--accent-primary)' : 'var(--text-primary)',
                  textDecoration: 'none',
                  transition: 'color var(--transition-base)',
                }}
                onMouseEnter={e => { if (!isActive(href)) e.currentTarget.style.color = 'var(--accent-primary)'; }}
                onMouseLeave={e => { if (!isActive(href)) e.currentTarget.style.color = 'var(--text-primary)'; }}
              >
                {label}
              </Link>
            ))}
            <a
              href="mailto:hello@randy.dev"
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-base)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                padding: 'var(--space-3) var(--space-8)',
                border: '1px solid rgba(232,185,49,0.3)',
              }}
            >
              CONTACT
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
```

- [ ] **Step 2: Visually verify in browser**

Check: Logo shows `RDG.` in gold monospace, nav links are uppercase with small letter-spacing, CONTACT button has gold border, active underline is 1px.

- [ ] **Step 3: Commit**

```bash
git add src/components/Navbar.jsx
git commit -m "feat: redesign navbar — RDG. logo, uppercase links, contact button"
```

---

## Task 5: Footer Update

**Files:**
- Modify: `src/components/Footer.jsx`

- [ ] **Step 1: Replace Footer.jsx**

```jsx
'use client';

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: '1px solid rgba(232,185,49,0.08)',
        padding: 'var(--space-8) 0',
        marginTop: 'auto',
        position: 'relative',
        zIndex: 6,
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
        }}
      >
        {/* Logo */}
        <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--accent-primary)', letterSpacing: '0.05em' }}>
          RDG<span style={{ color: 'rgba(232,185,49,0.4)' }}>.</span>
        </span>

        {/* Copyright */}
        <p style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', margin: 0 }}>
          © {new Date().getFullYear()} — REAL ESTATE AI AUTOMATION
        </p>

        {/* Links */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)' }}>
          {[{ label: 'GITHUB', href: '#' }, { label: 'LINKEDIN', href: '#' }].map(({ label, href }) => (
            <a
              key={label}
              href={href}
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.12em',
                color: 'var(--text-muted)',
                textDecoration: 'none',
                transition: 'color var(--transition-base)',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-secondary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              {label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/Footer.jsx
git commit -m "feat: update footer to match editorial style"
```

---

## Task 6: Homepage Redesign

**Files:**
- Rewrite: `src/app/page.js`

Full replacement. Remove GlassCard, ParallaxBackground, all Dutch project content. Replace with 5 bold editorial scroll-snap sections.

- [ ] **Step 1: Replace page.js entirely**

```jsx
'use client';

import { motion } from 'framer-motion';
import AnimateIn from '../components/AnimateIn';
import StaggerChildren from '../components/StaggerChildren';

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
  return (
    <div className="homepage-scroll">

      {/* ─────────────────────────────────────────────────────── */}
      {/* SECTION 1 — HERO                                       */}
      {/* ─────────────────────────────────────────────────────── */}
      <section
        className="snap-section"
        style={{
          height: 'calc(100vh - 4rem)',
          minHeight: 'unset',
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        <div className="container" style={{ paddingTop: 'var(--space-16)', paddingBottom: 'var(--space-16)' }}>
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

        {/* Scroll indicator */}
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute', bottom: 'var(--space-8)', left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px',
            color: 'rgba(232,185,49,0.4)',
          }}
        >
          <svg width="20" height="12" viewBox="0 0 20 12" fill="none">
            <path d="M1 1l9 9 9-9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
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
              <div
                key={cap.title}
                style={{
                  padding: 'var(--space-6)',
                  border: '1px solid rgba(232,185,49,0.1)',
                  borderLeft: `2px solid ${cap.accent === 'full' ? 'var(--accent-primary)' : cap.accent === 'mid' ? 'rgba(232,185,49,0.5)' : 'rgba(232,185,49,0.25)'}`,
                  transition: 'background-color var(--transition-base), border-color var(--transition-base)',
                  cursor: 'default',
                }}
                onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(232,185,49,0.03)'; }}
                onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; }}
              >
                <div style={{ fontFamily: 'monospace', fontSize: '20px', color: 'var(--accent-primary)', marginBottom: 'var(--space-4)', opacity: 0.8 }}>{cap.icon}</div>
                <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 'var(--text-base)', color: 'var(--text-primary)', marginBottom: 'var(--space-2)', letterSpacing: '0.02em' }}>{cap.title}</div>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.65, margin: 0 }}>{cap.desc}</p>
              </div>
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
              <motion.div
                key={project.title}
                whileHover={{ backgroundColor: 'rgba(232,185,49,0.03)', borderLeftColor: 'var(--accent-primary)' }}
                transition={{ duration: 0.15 }}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  gap: 'var(--space-4)',
                  padding: 'var(--space-4) var(--space-4)',
                  borderLeft: '2px solid transparent',
                  borderBottom: '1px solid rgba(232,185,49,0.06)',
                  transition: 'background-color var(--transition-fast), border-left-color var(--transition-fast)',
                }}
              >
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
              </motion.div>
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
              Let's talk about what AI can do for your real estate workflow.
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
```

- [ ] **Step 2: Visually verify all 5 sections**

Run: `npm run dev` (if not already running)
Check each section by scrolling:
1. Hero: large stacked headline, animated in sequence, gold CTA button
2. Capabilities: 3 bordered cards with left-accent, stagger entrance
3. Projects: 4 rows with tags and status badges, hover shows gold left-border
4. About: 3-line stacked headline, stat blocks, bilingual copy
5. CTA: centered, gold button

- [ ] **Step 3: Commit**

```bash
git add src/app/page.js
git commit -m "feat: full homepage redesign — 5 editorial sections, no GlassCard"
```

---

## Task 7: /work Page Redesign

**Files:**
- Rewrite: `src/app/work/page.js`

- [ ] **Step 1: Replace work/page.js**

```jsx
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
```

- [ ] **Step 2: Verify in browser at /work**

Check: 4 project cards with gold left-border hover, features list with gold dash markers, status badges.

- [ ] **Step 3: Commit**

```bash
git add src/app/work/page.js
git commit -m "feat: redesign /work with PropTech projects and editorial style"
```

---

## Task 8: /about Page Redesign

**Files:**
- Rewrite: `src/app/about/page.js`

- [ ] **Step 1: Replace about/page.js**

```jsx
'use client';

import AnimateIn from '../../components/AnimateIn';

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
              I'm Randy — a self-taught developer specialising in AI automation for the real estate sector. I build the systems that turn raw property data into decisions.
            </p>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 'var(--space-4)' }}>
              Ik leer het liefst door te bouwen. Elk concept dat ik interessant vind vertaalt zich in een project — zo begrijp ik het echt.
            </p>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 'var(--space-4)' }}>
              Currently exploring: automated valuation models, Dutch property data APIs, and LLM pipelines for lease contract analysis.
            </p>

            <div style={{ marginBottom: 'var(--space-8)', padding: 'var(--space-4) var(--space-5)', borderLeft: '2px solid var(--accent-primary)', backgroundColor: 'rgba(232,185,49,0.03)' }}>
              <p style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', margin: 0, lineHeight: 1.6 }}>
                "Geen buzzwords — alleen pipelines die draaien."
              </p>
            </div>

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

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
              {stack.map((group, i) => (
                <div key={group.category}>
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
                  {i < stack.length - 1 && <div style={{ marginTop: 'var(--space-8)', height: '1px', backgroundColor: 'rgba(232,185,49,0.08)' }} />}
                </div>
              ))}
            </div>
          </AnimateIn>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify at /about**

Check: Two-column layout, stacked editorial headline, quote block with gold left-border, monospace section labels, stack chips with gold tint.

- [ ] **Step 3: Commit**

```bash
git add src/app/about/page.js
git commit -m "feat: reposition /about as PropTech developer profile"
```

---

## Task 9: /blog Page Content Update

**Files:**
- Rewrite: `src/app/blog/page.js`

- [ ] **Step 1: Replace blog/page.js**

```jsx
'use client';

import { motion } from 'framer-motion';
import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';

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
            <motion.article
              key={post.title}
              whileHover={{ backgroundColor: 'rgba(232,185,49,0.02)', borderLeftColor: 'var(--accent-primary)' }}
              transition={{ duration: 0.15 }}
              style={{
                padding: 'var(--space-8) var(--space-4)',
                borderLeft: '2px solid transparent',
                borderBottom: i < posts.length - 1 ? '1px solid rgba(232,185,49,0.06)' : 'none',
                transition: 'background-color var(--transition-fast), border-left-color var(--transition-fast)',
              }}
            >
              <a href={post.href} style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
                <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>{post.date}</span>
                  <span style={{ color: 'rgba(232,185,49,0.2)' }}>·</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>{post.readTime} read</span>
                </div>
                <h2
                  style={{
                    fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xl)', fontWeight: 700,
                    color: 'var(--text-primary)', marginBottom: 'var(--space-3)', letterSpacing: '-0.01em',
                    transition: 'color var(--transition-fast)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
                >
                  {post.title}
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
                  {post.preview}
                </p>
                <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent-secondary)' }}>
                  READ →
                </span>
              </a>
            </motion.article>
          ))}
        </StaggerChildren>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify at /blog**

Check: 3 RE/AI post titles, gold left-border on hover, monospace date/time labels, "FIELD NOTES." editorial headline.

- [ ] **Step 3: Commit**

```bash
git add src/app/blog/page.js
git commit -m "feat: update /blog with Real Estate AI content"
```

---

## Task 10: Final Build Verification

- [ ] **Step 1: Run production build**

```bash
npm run build
```

Expected output: 
```
✓ Compiled successfully
Route (app)            Size
/                      ...
/about                 ...
/blog                  ...
/work                  ...
```
No TypeScript errors, no missing import errors.

- [ ] **Step 2: Spot-check each page in dev**

```bash
npm run dev
```

Verify on each page:
- `/` — Rotterdam SVG draws in over ~2.5s, scroll through all 5 sections, parallax layers visible
- `/work` — 4 project cards, gold border hover
- `/about` — two-column, monospace labels
- `/blog` — 3 RE posts, hover effects
- All pages: `RDG.` logo in navbar, CONTACT button visible, footer updated

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete randy.dev PropTech redesign — editorial layout, Rotterdam skyline, RE AI content"
```
