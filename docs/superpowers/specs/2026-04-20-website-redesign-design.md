# randy.dev — Visual Redesign Design Spec

**Date:** 2026-04-20
**Status:** Approved
**Approach:** C — Shared GlassCard component, Framer Motion parallax on hero/homepage, cinematic reveal on all other pages, aurora + raster background upgrade.

---

## Overview

A full visual upgrade of randy.dev that keeps the existing dark/gold design language but adds:
1. A shared `GlassCard` component (Style C: offset shadow, full perimeter glow, sweep on hover) used on all pages
2. A parallax hero with `herofoto.jpeg` as fullbleed background
3. Subtle scroll-driven parallax on the homepage, cinematic clip-path reveal on all other pages
4. An upgraded background: aurora pulse layer + blueprint raster replacing the existing DataGrid
5. Memory Agent added to the agents page as a featured spotlight card

---

## 1. Architecture — New & Changed Files

| File | Change |
|---|---|
| `src/components/GlassCard.jsx` | **New** — shared component, replaces local GlassCard in `page.js` |
| `src/components/AuroraBackground.tsx` | **New** — fixed aurora pulse layer |
| `src/app/layout.js` | Updated — adds AuroraBackground, replaces DataGrid with blueprint raster scroll effect |
| `public/herofoto.jpeg` | **New** — hero photo moved/copied to public/ |
| `src/app/page.js` | Updated — hero gets photo + parallax, imports shared GlassCard |
| `src/app/work/page.js` | Updated — project cards use GlassCard + cinematic reveal |
| `src/app/agents/page.js` | Updated — AgentCard uses GlassCard, Memory Agent featured spotlight added |
| `src/app/blog/page.js` | Updated — blog cards use GlassCard + cinematic reveal |
| `src/app/about/page.js` | Updated — bio blocks use GlassCard |
| `src/components/Navbar.jsx` | Updated — ensure Agents link is present |

---

## 2. GlassCard Component

**File:** `src/components/GlassCard.jsx`

**Props:**
- `offset` (boolean, default `true`) — shows the offset shadow pseudo-element behind the card
- `featured` (boolean, default `false`) — stronger gold border + permanent ambient glow, used for Memory Agent
- `style` (object) — passed through to the outer container for layout overrides
- `children` — React children

**Rest state styles:**
```
background: rgba(18,17,16,0.78)
backdrop-filter: blur(16px)
border: 1px solid rgba(232,185,49,0.18)
border-radius: 0  (sharp corners)
position: relative
overflow: hidden
transition: border-color 0.35s ease, transform 0.25s ease
```

**Offset shadow (::before via inline React trick — use a child div):**
```
position: absolute
inset: 8px -8px -8px 8px
border: 1px solid rgba(232,185,49,0.08)
z-index: -1
pointer-events: none
transition: border-color 0.3s ease
```
Implementation note: since inline styles can't use `::before`, implement as a sibling `<div>` with `position: absolute` inside a `position: relative` wrapper, rendered behind children via `z-index`.

**Hover state (via Framer Motion `whileHover`):**
```
borderColor: rgba(232,185,49,0.55)
x: -3, y: -3
boxShadow:
  -2px 0 16px rgba(232,185,49,0.18),
   2px 0 16px rgba(232,185,49,0.18),
   0 -2px 16px rgba(232,185,49,0.18),
   0  2px 16px rgba(232,185,49,0.18),
   0 0 40px rgba(232,185,49,0.10),
  inset 0 0 30px rgba(232,185,49,0.03)
```

**Sweep animation on hover:**
- Inner `<div>` child with `position: absolute`, full coverage, `pointerEvents: none`, `zIndex: 2`
- CSS `@keyframes sweep`: `linear-gradient(105deg, transparent 30%, rgba(232,185,49,0.06) 45%, rgba(232,185,49,0.10) 50%, rgba(232,185,49,0.06) 55%, transparent 70%)`
- Triggered via `useState(false)` — `onMouseEnter` sets `true`, `onMouseLeave` resets to `false`; a `motion.div` inside the card reads the state to apply the animation
- Duration: 0.6s, plays once per hover entry

**Featured variant (Memory Agent):**
```
border: 1px solid rgba(232,185,49,0.40)
boxShadow: 0 0 30px rgba(232,185,49,0.08)  (permanent)
```
Hover glow intensifies to `rgba(232,185,49,0.28)` on all sides.

**Cinematic reveal animation:**
- Wraps children in a `motion.div` with:
  ```
  initial: { clipPath: 'inset(0 100% 0 0)', opacity: 0 }
  whileInView: { clipPath: 'inset(0 0% 0 0)', opacity: 1 }
  viewport: { once: true, margin: '-60px' }
  transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] }
  ```
- Stagger across multiple cards via parent `StaggerChildren` (existing component, 0.1s delay per child)

---

## 3. Hero Section

**File:** `src/app/page.js` — first snap-section

**Layer stack (bottom to top):**

| z-index | Element | Notes |
|---|---|---|
| 0 | `<div>` with `background-image: url('/herofoto.jpeg')` | `filter: brightness(0.28) saturate(0.75)` + gold tint wash |
| 1 | Gradient mask div | Left vignette `rgba(18,17,16,0.92→0.35)` + top/bottom fade |
| 2 | NetworkBackground canvas (existing, layout-level) | Sits over photo |
| 10 | Text content div | Title + subtitle + CTAs |

**Parallax implementation:**
- `onMouseMove` handler on the hero `<section>`
- Photo layer: `transform: translate(${cx * 38}px, ${cy * 22}px)` where cx/cy are normalized -0.5..0.5
- Text layer: `transform: translate(${cx * -14}px, ${cy * -9}px)` (opposite direction)
- Both layers: `transition: transform 0.1s linear` during move, `0.6s ease` on mouseleave reset
- `will-change: transform` on both layers

**Text readability:**
- Title lines: `text-shadow: 0 2px 20px rgba(18,17,16,0.8), 0 0 60px rgba(18,17,16,0.6)`
- Subtitle: `text-shadow: 0 1px 12px rgba(18,17,16,0.9)`
- Left gradient mask provides primary protection

**Scroll indicator:**
- Bottom-left of hero, `position: absolute`
- 32px gold scan line with `@keyframes` sweep animation (left to right, 1.8s loop)
- Label: `// SCROLL TO EXPLORE` in monospace, `rgba(237,232,220,0.3)`
- Fades out on first scroll via `IntersectionObserver` or Framer Motion `useScroll`

**Photo asset:** `herofoto.jpeg` copied to `public/herofoto.jpeg`, referenced as `/herofoto.jpeg`.

---

## 4. Scroll Animations

**Homepage (scroll-snap sections):**
- Existing `AnimateIn` + `StaggerChildren` components remain
- GlassCard cinematic reveal fires when card enters viewport
- No additional parallax on non-hero sections (scroll-snap jumps between sections, parallax wouldn't be visible)

**All other pages (`/work`, `/about`, `/blog`, `/agents`):**
- GlassCard cinematic reveal: clip-path wipe from right, 0.7s, once per session
- StaggerChildren wraps card grids for 0.1s stagger between items
- No full-page parallax (pages don't use scroll-snap)

---

## 5. Background Upgrade

### AuroraBackground component

**File:** `src/components/AuroraBackground.tsx`

Three radial gradient orbs, pure CSS animation, zero JS after mount:

```
Orb 1: top-left, 800×600px ellipse, rgba(232,185,49,0.07), 14s cycle, opacity 0.06→0.12→0.06
Orb 2: bottom-right, 600×800px ellipse, rgba(232,185,49,0.05), 19s cycle, phase-shifted 7s
Orb 3: center, 400×400px circle, rgba(232,185,49,0.04), 24s cycle, phase-shifted 12s
```

- `position: fixed`, `inset: 0`, `zIndex: 0`, `pointerEvents: none`
- `mix-blend-mode: screen` for a natural glow interaction with the dark background

### Blueprint raster

Replaces existing `DataGrid` component. Implemented inline in `layout.js` as a fixed div:

```css
background-image:
  linear-gradient(rgba(232,185,49,0.03) 1px, transparent 1px),
  linear-gradient(90deg, rgba(232,185,49,0.03) 1px, transparent 1px);
background-size: 60px 60px;
```

Scroll parallax: `useEffect` attaches `scroll` listener, sets `transform: translateY(${scrollY * 0.15}px)` on the raster div. Creates subtle depth as content scrolls over a "fixed-but-drifting" grid.

### Layer order after upgrade

| z-index | Layer |
|---|---|
| 0 | AuroraBackground (new) |
| 1 | Blueprint raster (replaces DataGrid) |
| 2 | NetworkBackground canvas (existing) |
| 5 | Vignette overlay (existing) |
| 6+ | Page content |

---

## 6. Agents Page — Memory Agent Spotlight

**File:** `src/app/agents/page.js`

### Memory Agent data entry

Added to the `agents` array as the first item:

```js
{
  id: 'memory',
  name: 'Memory Agent',
  cli: 'memory',
  featured: true,
  description: 'Persistent memory layer of the multi-agent system. Stores project context, architectural decisions, and agent history — delivers ranked, relevant context to other agents on demand.',
  status: 'Live',
  statusStyle: { /* green */ },
  tags: ['Python', 'EventBus', 'JSON Store', 'Relevance Scoring'],
  phases: [
    { label: 'MemoryStore', detail: 'CRUD + pruning + JSON persistence. Flat key-value store with category (context/decisions/history) and keyword metadata.' },
    { label: 'MemoryIndexer', detail: 'EventBus wildcard subscriber. On every agent event, writes a summary to history; routes specific event types to other categories via EVENT_CATEGORY_MAP.' },
    { label: 'ContextBuilder', detail: 'Query → ranked MemoryEntry list. Scores by substring relevance + linear recency decay (horizon: 365 days). Returns top-N entries.' },
    { label: 'MemoryAgent', detail: 'BaseAgent subclass. Dispatches subcommands: store, query, list, clear. Integrates with AgentRegistry and StateStore.' },
  ],
  commands: [
    { label: 'Store a memory', cmd: 'python main.py memory store --category context --content "..." --keywords arch,api' },
    { label: 'Query memories', cmd: 'python main.py memory query --q "architecture decisions"' },
    { label: 'List all memories', cmd: 'python main.py memory list' },
    { label: 'Clear category', cmd: 'python main.py memory clear --category history' },
  ],
}
```

### Featured card layout

The Memory Agent card uses `featured={true}` on GlassCard and renders a two-column layout inside:
- **Left column:** eyebrow `NEW // MEMORY AGENT` with blinking cursor, title, description, status badge + `v0.1` tag, tags
- **Right column:** "memory feed" — a decorative `<ul>` of 4–5 simulated memory entries that fade in one by one on page load (Framer Motion stagger, 0.3s between items). Entries are static strings styled as `> [category] key: value` in monospace gold.

### Page header — typing animation

Below the existing subtitle, a new line:
```
> 4 agents registered. 1 new.
```
Implemented as a client-side typewriter: `useEffect` sets a character-reveal interval of 40ms, starts after 1200ms delay. Cursor blinks for 2s then disappears.

### Navbar

`/agents` is already present in `NAV_LINKS` in `Navbar.jsx` — no changes needed.

---

## Out of Scope

- No changes to routing or URL structure
- No changes to the Calendar page (`/calendar`)
- No CMS, database, or API additions
- No changes to `NetworkBackground.tsx` canvas rendering logic
- No mobile-specific parallax (parallax disabled via `@media (prefers-reduced-motion: reduce)`)

---

## Constraints & Notes

- All styles remain inline React style objects per project convention — no CSS framework additions
- CSS variables from `globals.css` used throughout, no hardcoded color values
- `'use client'` directive on all modified page files (already present)
- `herofoto.jpeg` must be in `public/` for Next.js static serving
- Aurora CSS animations must include `prefers-reduced-motion` media query override (disables animation, keeps static gradient)
- GlassCard sweep animation triggered via `useState` on `onMouseEnter`, reset on `onMouseLeave`
