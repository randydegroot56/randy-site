# Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade randy.dev with shared GlassCard (offset shadow + perimeter glow), parallax hero with herofoto.jpeg, aurora + raster background, and Memory Agent spotlight on the agents page.

**Architecture:** Approach C — new shared `GlassCard` component used on all pages, Framer Motion `whileInView` clip-path reveal for cinematic entrance, mouse-driven parallax only on the homepage hero. Background upgraded with `AuroraBackground` (breathing gold gradients) and `BlueprintRaster` (scrolling grid) replacing the existing `DataGrid`.

**Tech Stack:** Next.js 14.2, React 18, Framer Motion 12, inline React style objects, CSS variables from `globals.css`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `public/herofoto.jpeg` | Create (copy) | Static asset for hero background |
| `src/components/GlassCard.jsx` | Create | Shared card: offset shadow, perimeter glow, sweep, clip-path reveal |
| `src/components/AuroraBackground.tsx` | Create | Fixed aurora pulse layer (3 breathing gold gradient orbs) |
| `src/components/BlueprintRaster.jsx` | Create | Fixed grid lines that drift on scroll — replaces DataGrid |
| `src/app/layout.js` | Modify | Add AuroraBackground, replace DataGrid with BlueprintRaster |
| `src/app/page.js` | Modify | Hero photo + parallax + scroll indicator; capability/project cards → GlassCard |
| `src/app/work/page.js` | Modify | Project articles → GlassCard |
| `src/app/blog/page.js` | Modify | Blog articles → GlassCard |
| `src/app/about/page.js` | Modify | Quote block + stack category items → GlassCard |
| `src/app/agents/page.js` | Modify | AgentCard → GlassCard; Memory Agent featured spotlight + typing animation |

---

## Task 1: Copy hero photo to public/

**Files:**
- Create: `public/herofoto.jpeg`

- [ ] **Step 1: Copy the photo**

```bash
cp herofoto.jpeg public/herofoto.jpeg
```

Verify: `ls public/herofoto.jpeg` — file should exist.

- [ ] **Step 2: Commit**

```bash
git add public/herofoto.jpeg
git commit -m "feat(assets): add hero photo to public/"
```

---

## Task 2: Create GlassCard component

**Files:**
- Create: `src/components/GlassCard.jsx`

- [ ] **Step 1: Create the file**

```jsx
'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Shared glass card — Style C: offset shadow + full perimeter glow + sweep on hover.
 *
 * Props:
 *   offset   {boolean}    Show offset shadow behind card. Default: true.
 *   featured {boolean}    Stronger gold border + permanent ambient glow. Default: false.
 *   reveal   {boolean}    Clip-path wipe-in when scrolled into view. Default: true.
 *   style    {object}     Applied to the outermost wrapper for layout overrides.
 *   children {ReactNode}
 */
export default function GlassCard({
  children,
  offset = true,
  featured = false,
  reveal = true,
  style = {},
}) {
  const [hovered, setHovered] = useState(false);

  const baseBorder  = featured ? 'rgba(232,185,49,0.40)' : 'rgba(232,185,49,0.18)';
  const hoverBorder = featured ? 'rgba(232,185,49,0.65)' : 'rgba(232,185,49,0.55)';

  const baseBoxShadow = featured ? '0 0 30px rgba(232,185,49,0.08)' : 'none';
  const hoverBoxShadow = featured
    ? '-2px 0 16px rgba(232,185,49,0.28), 2px 0 16px rgba(232,185,49,0.28), 0 -2px 16px rgba(232,185,49,0.28), 0 2px 16px rgba(232,185,49,0.28), 0 0 40px rgba(232,185,49,0.14), inset 0 0 30px rgba(232,185,49,0.04)'
    : '-2px 0 16px rgba(232,185,49,0.18), 2px 0 16px rgba(232,185,49,0.18), 0 -2px 16px rgba(232,185,49,0.18), 0 2px 16px rgba(232,185,49,0.18), 0 0 40px rgba(232,185,49,0.10), inset 0 0 30px rgba(232,185,49,0.03)';

  const card = (
    <div style={{ position: 'relative', ...style }}>
      {/* Offset shadow — positioned behind the main card */}
      {offset && (
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: '8px -8px -8px 8px',
            border: `1px solid ${hovered ? 'rgba(232,185,49,0.20)' : 'rgba(232,185,49,0.08)'}`,
            pointerEvents: 'none',
            transition: 'border-color 0.3s ease',
          }}
        />
      )}

      {/* Main card surface */}
      <motion.div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        animate={{
          x: hovered ? -3 : 0,
          y: hovered ? -3 : 0,
          borderColor: hovered ? hoverBorder : baseBorder,
          boxShadow: hovered ? hoverBoxShadow : baseBoxShadow,
        }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        style={{
          position: 'relative',
          background: 'rgba(18,17,16,0.78)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: `1px solid ${baseBorder}`,
          borderRadius: 0,
          overflow: 'hidden',
        }}
      >
        {/* Diagonal sweep on hover — plays once per hover entry */}
        <AnimatePresence>
          {hovered && (
            <motion.div
              key="sweep"
              initial={{ x: '-150%' }}
              animate={{ x: '150%' }}
              transition={{ duration: 0.6, ease: 'easeInOut' }}
              style={{
                position: 'absolute',
                inset: 0,
                background:
                  'linear-gradient(105deg, transparent 30%, rgba(232,185,49,0.06) 45%, rgba(232,185,49,0.10) 50%, rgba(232,185,49,0.06) 55%, transparent 70%)',
                pointerEvents: 'none',
                zIndex: 2,
              }}
            />
          )}
        </AnimatePresence>

        {/* Content — above sweep */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </div>
      </motion.div>
    </div>
  );

  if (!reveal) return card;

  return (
    <motion.div
      initial={{ clipPath: 'inset(0 100% 0 0)', opacity: 0 }}
      whileInView={{ clipPath: 'inset(0 0% 0 0)', opacity: 1 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
    >
      {card}
    </motion.div>
  );
}
```

- [ ] **Step 2: Verify build compiles**

```bash
npm run build
```

Expected: no TypeScript/ESLint errors. If errors, fix before continuing.

- [ ] **Step 3: Commit**

```bash
git add src/components/GlassCard.jsx
git commit -m "feat(components): add shared GlassCard with offset shadow, perimeter glow, clip-path reveal"
```

---

## Task 3: Create AuroraBackground component

**Files:**
- Create: `src/components/AuroraBackground.tsx`

- [ ] **Step 1: Create the file**

```tsx
export default function AuroraBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      <style>{`
        @keyframes aurora1 {
          0%, 100% { opacity: 0.06; transform: scale(1) translate(0, 0); }
          50%       { opacity: 0.12; transform: scale(1.1) translate(2%, 1%); }
        }
        @keyframes aurora2 {
          0%, 100% { opacity: 0.04; transform: scale(1) translate(0, 0); }
          50%       { opacity: 0.09; transform: scale(1.08) translate(-2%, -1%); }
        }
        @keyframes aurora3 {
          0%, 100% { opacity: 0.03; transform: scale(1); }
          50%       { opacity: 0.07; transform: scale(1.05); }
        }
        @media (prefers-reduced-motion: reduce) {
          .aurora-orb { animation: none !important; }
        }
      `}</style>

      {/* Orb 1 — top-left, 14 s */}
      <div
        className="aurora-orb"
        style={{
          position: 'absolute',
          top: '-10%',
          left: '-5%',
          width: '55%',
          height: '60%',
          background: 'radial-gradient(ellipse, rgba(232,185,49,0.18) 0%, transparent 70%)',
          animation: 'aurora1 14s ease-in-out infinite',
        }}
      />

      {/* Orb 2 — bottom-right, 19 s, phase-shifted 7 s */}
      <div
        className="aurora-orb"
        style={{
          position: 'absolute',
          bottom: '-15%',
          right: '-5%',
          width: '50%',
          height: '55%',
          background: 'radial-gradient(ellipse, rgba(232,185,49,0.12) 0%, transparent 70%)',
          animation: 'aurora2 19s ease-in-out 7s infinite',
        }}
      />

      {/* Orb 3 — center, 24 s, phase-shifted 12 s */}
      <div
        className="aurora-orb"
        style={{
          position: 'absolute',
          top: '30%',
          left: '35%',
          width: '35%',
          height: '40%',
          background: 'radial-gradient(ellipse, rgba(232,185,49,0.08) 0%, transparent 70%)',
          animation: 'aurora3 24s ease-in-out 12s infinite',
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/AuroraBackground.tsx
git commit -m "feat(components): add AuroraBackground with breathing gold gradient orbs"
```

---

## Task 4: Create BlueprintRaster component

**Files:**
- Create: `src/components/BlueprintRaster.jsx`

- [ ] **Step 1: Create the file**

```jsx
'use client';

import { useEffect, useRef } from 'react';

export default function BlueprintRaster() {
  const ref = useRef(null);

  useEffect(() => {
    function onScroll() {
      if (ref.current) {
        ref.current.style.transform = `translateY(${window.scrollY * 0.15}px)`;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1,
        pointerEvents: 'none',
        backgroundImage: `
          linear-gradient(rgba(232,185,49,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(232,185,49,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
      }}
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/BlueprintRaster.jsx
git commit -m "feat(components): add BlueprintRaster grid with scroll parallax"
```

---

## Task 5: Update layout.js — add Aurora + Raster, remove DataGrid

**Files:**
- Modify: `src/app/layout.js`

- [ ] **Step 1: Replace DataGrid import, add new imports**

In `src/app/layout.js`, replace:
```js
import DataGrid from '../components/DataGrid';
```
with:
```js
import AuroraBackground from '../components/AuroraBackground';
import BlueprintRaster from '../components/BlueprintRaster';
```

- [ ] **Step 2: Replace DataGrid usage in JSX**

Replace:
```jsx
{/* Layer 1: subtle data grid (slowest parallax) */}
<DataGrid />
```
with:
```jsx
{/* Layer 0: aurora pulse (slowest, fixed) */}
<AuroraBackground />

{/* Layer 1: blueprint raster grid (scroll parallax) */}
<BlueprintRaster />
```

The `NetworkBackground` block and vignette overlay stay unchanged.

- [ ] **Step 3: Verify build**

```bash
npm run build
```

Expected: clean build. The DataGrid component is no longer imported — do not delete its file yet (it may be used elsewhere; run `grep -r "DataGrid" src/` first, delete only if unused).

- [ ] **Step 4: Commit**

```bash
git add src/app/layout.js
git commit -m "feat(layout): replace DataGrid with AuroraBackground + BlueprintRaster"
```

---

## Task 6: Update homepage hero — photo background + mouse parallax + scan-line indicator

**Files:**
- Modify: `src/app/page.js`

- [ ] **Step 1: Add useRef import**

At the top of `src/app/page.js`, change:
```js
import { motion } from 'framer-motion';
```
to:
```js
import { useRef } from 'react';
import { motion } from 'framer-motion';
```

- [ ] **Step 2: Add parallax refs and handlers inside the Page component**

Inside `export default function Page() {`, add at the top of the function body (before the return):

```jsx
const photoRef = useRef(null);
const textRef  = useRef(null);

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
  [photoRef, textRef].forEach((ref, i) => {
    if (!ref.current) return;
    ref.current.style.transition = 'transform 0.6s ease';
    ref.current.style.transform  = 'translate(0,0)';
    setTimeout(() => {
      if (ref.current) ref.current.style.transition = 'transform 0.1s linear';
    }, 600);
  });
}
```

- [ ] **Step 3: Replace the hero section JSX**

Find the current hero `<section>` (first snap-section, `height: 'calc(100vh - 4rem)'`). Replace the entire section with:

```jsx
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
      filter: 'brightness(0.28) saturate(0.75)',
      willChange: 'transform',
      transition: 'transform 0.1s linear',
    }}
  />

  {/* Layer 1: Gold tint wash over photo */}
  <div
    aria-hidden="true"
    style={{
      position: 'absolute',
      inset: 0,
      background:
        'linear-gradient(135deg, rgba(232,185,49,0.06) 0%, transparent 50%, rgba(232,185,49,0.03) 100%)',
      pointerEvents: 'none',
    }}
  />

  {/* Layer 2: Readability gradient mask */}
  <div
    aria-hidden="true"
    style={{
      position: 'absolute',
      inset: 0,
      background: [
        'linear-gradient(90deg, rgba(18,17,16,0.92) 0%, rgba(18,17,16,0.75) 40%, rgba(18,17,16,0.35) 70%, rgba(18,17,16,0.55) 100%)',
        'linear-gradient(180deg, rgba(18,17,16,0.5) 0%, transparent 20%, transparent 80%, rgba(18,17,16,0.6) 100%)',
      ].join(', '),
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
      <div style={{
        position: 'absolute',
        inset: 0,
        background: '#E8B931',
        animation: 'scanLine 1.8s ease-in-out infinite',
      }} />
    </div>
    <span style={{
      fontFamily: 'monospace',
      fontSize: '9px',
      letterSpacing: '0.18em',
      textTransform: 'uppercase',
      color: 'rgba(237,232,220,0.3)',
    }}>
      Scroll to explore
    </span>
  </motion.div>
</section>
```

- [ ] **Step 4: Verify build**

```bash
npm run build
```

Expected: clean build.

- [ ] **Step 5: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): add fullbleed photo background with mouse parallax and scan-line indicator"
```

---

## Task 7: Update homepage non-hero sections — capability cards + project rows → GlassCard

**Files:**
- Modify: `src/app/page.js`

- [ ] **Step 1: Remove the local GlassCard component**

Delete the entire `function GlassCard(...)` definition from `src/app/page.js` (it's defined locally near the top of the file, before the `Page` component).

- [ ] **Step 2: Add GlassCard import**

Add to imports at the top of `src/app/page.js`:
```js
import GlassCard from '../components/GlassCard';
```

- [ ] **Step 3: Wrap capability cards in GlassCard**

In the capabilities section, replace each capability card `<div>`:

```jsx
// Before (inside the StaggerChildren map):
<div
  key={cap.title}
  style={{
    padding: 'var(--space-6)',
    border: '1px solid rgba(232,185,49,0.1)',
    borderLeft: `2px solid ...`,
    ...
  }}
  onMouseEnter={...}
  onMouseLeave={...}
>
  ...
</div>

// After:
<GlassCard key={cap.title} style={{ marginBottom: 0 }}>
  <div style={{ padding: 'var(--space-6)' }}>
    <div style={{ fontFamily: 'monospace', fontSize: '20px', color: 'var(--accent-primary)', marginBottom: 'var(--space-4)', opacity: 0.8 }}>{cap.icon}</div>
    <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 'var(--text-base)', color: 'var(--text-primary)', marginBottom: 'var(--space-2)', letterSpacing: '0.02em' }}>{cap.title}</div>
    <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.65, margin: 0 }}>{cap.desc}</p>
  </div>
</GlassCard>
```

Note: remove the `onMouseEnter`/`onMouseLeave` handlers — GlassCard handles hover internally.

- [ ] **Step 4: Wrap project rows in GlassCard**

In the projects section, replace each `motion.div` row:

```jsx
// Before:
<motion.div
  key={project.title}
  whileHover={{ backgroundColor: 'rgba(232,185,49,0.03)', borderLeftColor: 'var(--accent-primary)' }}
  transition={{ duration: 0.15 }}
  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', ... }}
>
  ...
</motion.div>

// After:
<GlassCard key={project.title} style={{ marginBottom: 0 }}>
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
```

- [ ] **Step 5: Verify build**

```bash
npm run build
```

Expected: clean build, no reference to the old local GlassCard.

- [ ] **Step 6: Commit**

```bash
git add src/app/page.js
git commit -m "feat(home): capability cards + project rows use shared GlassCard"
```

---

## Task 8: Update work/page.js — project articles → GlassCard

**Files:**
- Modify: `src/app/work/page.js`

- [ ] **Step 1: Add GlassCard import, remove motion import if unused**

Add to imports:
```js
import GlassCard from '../../components/GlassCard';
```

- [ ] **Step 2: Replace each motion.article with GlassCard**

```jsx
// Before:
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
  {/* ...content... */}
</motion.article>

// After:
<GlassCard key={project.title}>
  <div style={{ padding: 'var(--space-8)' }}>
    {/* ...same content, unchanged... */}
  </div>
</GlassCard>
```

Keep all content inside unchanged — just move it inside `<GlassCard><div style={{ padding: 'var(--space-8)' }}>...</div></GlassCard>`.

- [ ] **Step 3: Remove the motion import if motion is no longer used**

Check if `motion` is used anywhere else in the file. If not, remove it from the import line:
```js
// Remove: import { motion } from 'framer-motion';
// Keep if StaggerChildren or other imports still need it
```

- [ ] **Step 4: Verify build**

```bash
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add src/app/work/page.js
git commit -m "feat(work): project cards use shared GlassCard with cinematic reveal"
```

---

## Task 9: Update blog/page.js — post articles → GlassCard

**Files:**
- Modify: `src/app/blog/page.js`

- [ ] **Step 1: Add GlassCard import**

```js
import GlassCard from '../../components/GlassCard';
```

- [ ] **Step 2: Replace each motion.article**

Find the `posts.map()` block. Replace:

```jsx
// Before:
<motion.article
  key={post.title}
  whileHover={{ backgroundColor: 'rgba(232,185,49,0.02)', borderLeftColor: 'var(--accent-primary)' }}
  transition={{ duration: 0.15 }}
  style={{
    padding: 'var(--space-8) var(--space-4)',
    borderLeft: '2px solid transparent',
    ...
  }}
>
  {/* ...content... */}
</motion.article>

// After:
<GlassCard key={post.title}>
  <div style={{ padding: 'var(--space-8) var(--space-4)' }}>
    {/* ...same content, unchanged... */}
  </div>
</GlassCard>
```

- [ ] **Step 3: Remove motion import if unused**

Check if `motion` is used elsewhere in the file. Remove from import if not.

- [ ] **Step 4: Verify build and commit**

```bash
npm run build
git add src/app/blog/page.js
git commit -m "feat(blog): post cards use shared GlassCard with cinematic reveal"
```

---

## Task 10: Update about/page.js — quote block + stack categories → GlassCard

**Files:**
- Modify: `src/app/about/page.js`

- [ ] **Step 1: Add GlassCard import**

```js
import GlassCard from '../../components/GlassCard';
```

- [ ] **Step 2: Wrap the quote block in GlassCard**

Find:
```jsx
<div style={{ marginBottom: 'var(--space-8)', padding: 'var(--space-4) var(--space-5)', borderLeft: '2px solid var(--accent-primary)', backgroundColor: 'rgba(232,185,49,0.03)' }}>
  <p style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', margin: 0, lineHeight: 1.6 }}>
    &ldquo;Geen buzzwords — alleen pipelines die draaien.&rdquo;
  </p>
</div>
```

Replace with:
```jsx
<GlassCard style={{ marginBottom: 'var(--space-8)' }}>
  <div style={{ padding: 'var(--space-4) var(--space-5)' }}>
    <p style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', margin: 0, lineHeight: 1.6 }}>
      &ldquo;Geen buzzwords — alleen pipelines die draaien.&rdquo;
    </p>
  </div>
</GlassCard>
```

- [ ] **Step 3: Wrap each stack category in GlassCard**

Find the right column stack rendering. Each `stack` item currently renders as a `<div>` with skills list. Wrap each in GlassCard:

```jsx
// Before:
<div key={item.category} style={{ padding: 'var(--space-4)', border: '1px solid rgba(232,185,49,0.1)', ... }}>
  ...
</div>

// After:
<GlassCard key={item.category} style={{ marginBottom: 'var(--space-4)' }}>
  <div style={{ padding: 'var(--space-4)' }}>
    {/* same content */}
  </div>
</GlassCard>
```

Note: Read the full stack rendering code in `about/page.js` first (below line 60) to see the exact structure before replacing.

- [ ] **Step 4: Verify build and commit**

```bash
npm run build
git add src/app/about/page.js
git commit -m "feat(about): quote block and stack categories use shared GlassCard"
```

---

## Task 11: Update agents/page.js — Memory Agent featured spotlight + typing animation + GlassCard

This is the most complex task. Read the full current `agents/page.js` before starting (all 283 lines).

**Files:**
- Modify: `src/app/agents/page.js`

- [ ] **Step 1: Add imports**

Change imports to:
```js
'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GlassCard from '../../components/GlassCard';
import AnimateIn from '../../components/AnimateIn';
import StaggerChildren from '../../components/StaggerChildren';
```

- [ ] **Step 2: Add Memory Agent to the agents array — insert as first element**

Add before the `code-auditor` entry in the `agents` array:

```js
{
  id: 'memory',
  name: 'Memory Agent',
  cli: 'memory',
  featured: true,
  description:
    'Persistent memory layer of the multi-agent system. Stores project context, architectural decisions, and agent history — and delivers ranked, relevant context to other agents on demand via relevance + recency scoring.',
  status: 'Live',
  statusStyle: {
    bg: 'rgba(34,197,94,0.10)',
    border: 'rgba(34,197,94,0.25)',
    text: 'rgba(34,197,94,0.9)',
    dot: 'rgba(34,197,94,0.9)',
  },
  tags: ['Python', 'EventBus', 'JSON Store', 'Relevance Scoring', 'Recency Decay'],
  phases: [
    { label: 'MemoryStore', status: '✅ Live', detail: 'CRUD + pruning + JSON persistence. Flat key-value store with category (context / decisions / history) and keyword metadata. Auto-prunes entries older than the configured horizon.' },
    { label: 'MemoryIndexer', status: '✅ Live', detail: 'EventBus wildcard subscriber. On every agent event, writes a summary to history; routes specific event types to other categories via EVENT_CATEGORY_MAP.' },
    { label: 'ContextBuilder', status: '✅ Live', detail: 'Query → ranked MemoryEntry list. Scores by substring relevance (query words found in content + keywords) and linear recency decay (horizon: 365 days). Returns top-N entries.' },
    { label: 'MemoryAgent', status: '✅ Live', detail: 'BaseAgent subclass. Dispatches subcommands: store, query, list, clear. Integrates with AgentRegistry and StateStore.' },
  ],
  commands: [
    { label: 'Store a memory', cmd: 'python main.py memory store --category context --content "Next.js + Python agents" --keywords arch,stack' },
    { label: 'Query memories', cmd: 'python main.py memory query --q "architecture decisions"' },
    { label: 'List all memories', cmd: 'python main.py memory list' },
    { label: 'Clear a category', cmd: 'python main.py memory clear --category history' },
  ],
},
```

- [ ] **Step 3: Replace the AgentCard component**

Delete the existing `function AgentCard({ agent })` and replace with:

```jsx
// Decorative memory feed entries shown in the featured Memory Agent card
const MEMORY_FEED = [
  { cat: 'context',  key: 'project.stack',          value: 'Next.js + Python agents' },
  { cat: 'decision', key: 'orchestrator.routing',    value: 'INTENT_MAP dispatch' },
  { cat: 'history',  key: 'audit.last_run',          value: '2026-04-20T09:14:00Z' },
  { cat: 'context',  key: 'agent.count',             value: '4 registered' },
  { cat: 'decision', key: 'memory.scoring',          value: 'substring + recency decay' },
];

function AgentCard({ agent }) {
  const [open, setOpen] = useState(false);

  if (agent.featured) {
    return (
      <GlassCard featured reveal>
        <div style={{ padding: 'var(--space-8)' }}>
          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
              {/* NEW label */}
              <span style={{
                fontFamily: 'monospace', fontSize: '9px', fontWeight: 700,
                letterSpacing: '0.18em', textTransform: 'uppercase',
                color: 'var(--accent-primary)',
                border: '1px solid rgba(232,185,49,0.4)',
                padding: '2px 8px',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <motion.span
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', backgroundColor: 'var(--accent-primary)' }}
                />
                NEW
              </span>
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
              <span style={{
                fontFamily: 'monospace', fontSize: '9px', fontWeight: 600,
                letterSpacing: '0.1em', color: 'var(--text-muted)',
                border: '1px solid rgba(237,232,220,0.08)',
                padding: '2px 7px',
              }}>
                v0.1
              </span>
            </div>

            <button
              onClick={() => setOpen(v => !v)}
              style={{
                flexShrink: 0, background: 'none',
                border: '1px solid rgba(232,185,49,0.2)',
                color: 'var(--accent-secondary)', fontFamily: 'monospace',
                fontSize: 'var(--text-xs)', padding: '0.3rem var(--space-3)',
                cursor: 'pointer', letterSpacing: '0.08em',
                transition: 'border-color var(--transition-fast), color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.color = 'var(--accent-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(232,185,49,0.2)'; e.currentTarget.style.color = 'var(--accent-secondary)'; }}
            >
              {open ? '[ COLLAPSE ]' : '[ MANUAL ]'}
            </button>
          </div>

          {/* Two-column body */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-8)', alignItems: 'start' }}>
            {/* Left: description + AGENT ID + tags */}
            <div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.75, marginBottom: 'var(--space-5)' }}>
                {agent.description}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
                <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>AGENT ID</span>
                <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', backgroundColor: 'rgba(232,185,49,0.05)', padding: '0.15rem var(--space-2)', border: '1px solid rgba(232,185,49,0.12)' }}>
                  {agent.cli}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                {agent.tags.map(tag => (
                  <span key={tag} style={{
                    padding: '0.2rem var(--space-3)',
                    fontSize: 'var(--text-xs)', fontFamily: 'var(--font-heading)', fontWeight: 500,
                    color: 'var(--text-muted)', backgroundColor: 'rgba(232,185,49,0.04)',
                    border: '1px solid rgba(232,185,49,0.1)',
                  }}>{tag}</span>
                ))}
              </div>
            </div>

            {/* Right: decorative live memory feed */}
            <div style={{
              borderLeft: '1px solid rgba(232,185,49,0.1)',
              paddingLeft: 'var(--space-6)',
            }}>
              <p style={{ fontFamily: 'monospace', fontSize: '9px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
                // LIVE MEMORY FEED
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {MEMORY_FEED.map((entry, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.3 + 0.5, duration: 0.4, ease: 'easeOut' }}
                    style={{ fontFamily: 'monospace', fontSize: '11px', lineHeight: 1.6 }}
                  >
                    <span style={{ color: 'rgba(232,185,49,0.4)' }}>[{entry.cat}]</span>
                    <span style={{ color: 'var(--text-muted)' }}> {entry.key}: </span>
                    <span style={{ color: 'rgba(232,185,49,0.7)' }}>{entry.value}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Expandable manual */}
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
              <div style={{ padding: 'var(--space-8)', paddingTop: 0, borderTop: '1px solid rgba(232,185,49,0.08)' }}>
                <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>COMPONENTS</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginBottom: 'var(--space-8)' }}>
                  {agent.phases.map((phase, i) => (
                    <div key={i} style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
                      <span style={{ width: 14, height: 1, backgroundColor: 'var(--accent-primary)', flexShrink: 0, marginTop: '0.6rem' }} />
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-1)' }}>
                          <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{phase.label}</span>
                          {phase.status && <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)' }}>{phase.status}</span>}
                        </div>
                        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>{phase.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
                <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>COMMANDS</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {agent.commands.map((c, i) => (
                    <div key={i}>
                      <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em', display: 'block', marginBottom: 'var(--space-1)' }}># {c.label}</span>
                      <div style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', backgroundColor: 'rgba(232,185,49,0.04)', border: '1px solid rgba(232,185,49,0.1)', padding: 'var(--space-3) var(--space-4)', wordBreak: 'break-all' }}>
                        <span style={{ color: 'var(--accent-primary)', userSelect: 'none' }}>$ </span>{c.cmd}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>
    );
  }

  // Standard agent card
  return (
    <GlassCard>
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
          <button
            onClick={() => setOpen(v => !v)}
            style={{
              flexShrink: 0, background: 'none',
              border: '1px solid rgba(232,185,49,0.2)',
              color: 'var(--accent-secondary)', fontFamily: 'monospace',
              fontSize: 'var(--text-xs)', padding: '0.3rem var(--space-3)',
              cursor: 'pointer', letterSpacing: '0.08em',
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

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
          <span style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>AGENT ID</span>
          <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', backgroundColor: 'rgba(232,185,49,0.05)', padding: '0.15rem var(--space-2)', border: '1px solid rgba(232,185,49,0.12)' }}>
            {agent.cli}
          </span>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
          {agent.tags.map(tag => (
            <span key={tag} style={{
              padding: '0.2rem var(--space-3)',
              fontSize: 'var(--text-xs)', fontFamily: 'var(--font-heading)', fontWeight: 500,
              color: 'var(--text-muted)', backgroundColor: 'rgba(232,185,49,0.04)',
              border: '1px solid rgba(232,185,49,0.1)',
            }}>{tag}</span>
          ))}
        </div>
      </div>

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
            <div style={{ padding: 'var(--space-8)', paddingTop: 0, borderTop: '1px solid rgba(232,185,49,0.08)' }}>
              <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
                {agent.id === 'orchestrator' ? 'COMPONENTS' : 'PHASES'}
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginBottom: 'var(--space-8)' }}>
                {agent.phases.map((phase, i) => (
                  <div key={i} style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
                    <span style={{ width: 14, height: 1, backgroundColor: 'var(--accent-primary)', flexShrink: 0, marginTop: '0.6rem' }} />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-1)' }}>
                        <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{phase.label}</span>
                        {phase.status && <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)' }}>{phase.status}</span>}
                      </div>
                      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>{phase.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ fontFamily: 'monospace', fontSize: '10px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>COMMANDS</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {agent.commands.map((c, i) => (
                  <div key={i}>
                    <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em', display: 'block', marginBottom: 'var(--space-1)' }}># {c.label}</span>
                    <div style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)', backgroundColor: 'rgba(232,185,49,0.04)', border: '1px solid rgba(232,185,49,0.1)', padding: 'var(--space-3) var(--space-4)', wordBreak: 'break-all' }}>
                      <span style={{ color: 'var(--accent-primary)', userSelect: 'none' }}>$ </span>{c.cmd}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}
```

- [ ] **Step 4: Add typing animation to AgentsPage**

Replace `export default function AgentsPage()` with:

```jsx
const TYPING_TARGET = '> 4 agents registered. 1 new.';

export default function AgentsPage() {
  const [typed, setTyped] = useState('');

  useEffect(() => {
    const startTimer = setTimeout(() => {
      let i = 0;
      const tick = setInterval(() => {
        i += 1;
        setTyped(TYPING_TARGET.slice(0, i));
        if (i >= TYPING_TARGET.length) clearInterval(tick);
      }, 40);
      return () => clearInterval(tick);
    }, 1200);
    return () => clearTimeout(startTimer);
  }, []);

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
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-md)', lineHeight: 1.7, maxWidth: '580px', marginBottom: 'var(--space-4)' }}>
            Specialized agents that audit, fix, and coordinate — built on a shared event-driven framework. Click <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--accent-secondary)' }}>[ MANUAL ]</span> to expand commands and documentation.
          </p>
          {/* Typing animation */}
          <p style={{ fontFamily: 'monospace', fontSize: '11px', color: 'var(--accent-secondary)', letterSpacing: '0.06em', marginBottom: 'var(--space-16)', minHeight: '1.4em' }}>
            {typed}
            {typed.length < TYPING_TARGET.length && (
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
                style={{ display: 'inline-block', width: 7, height: 12, backgroundColor: 'var(--accent-primary)', marginLeft: 2, verticalAlign: 'middle' }}
              />
            )}
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
```

- [ ] **Step 5: Verify build**

```bash
npm run build
```

Expected: clean build. If TypeScript errors appear related to the `featured` prop not being in the agents data type, the code uses plain JS so there are no type annotations to worry about.

- [ ] **Step 6: Commit**

```bash
git add src/app/agents/page.js
git commit -m "feat(agents): Memory Agent featured spotlight, GlassCard on all cards, typing animation"
```

---

## Task 12: Final verification

- [ ] **Step 1: Full production build**

```bash
npm run build
```

Expected: Build completes with no errors. Note any warnings but they are non-blocking.

- [ ] **Step 2: Start dev server and manually verify each page**

```bash
npm run dev
```

Check each route:
- `/` — Hero photo visible, parallax works on mouse move, scan-line animates, capability cards + project rows have GlassCard glow on hover
- `/work` — Project cards have GlassCard reveal + perimeter glow on hover
- `/blog` — Post cards have GlassCard reveal + perimeter glow on hover
- `/about` — Quote block + stack categories have GlassCard
- `/agents` — Typing animation starts after 1.2s, Memory Agent shows featured glow + memory feed stagger, other agents have GlassCard glow
- All pages — Aurora pulse visible in background, raster grid visible, raster drifts slightly on scroll

- [ ] **Step 3: Check `prefers-reduced-motion` respected**

In browser devtools: Rendering tab → Emulate CSS media feature `prefers-reduced-motion: reduce`. Verify aurora orbs stop animating (static gradient remains), scan-line stops, typing animation still runs (it's not a CSS animation).

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: visual redesign complete — GlassCard, parallax hero, aurora background, Memory Agent spotlight"
```
