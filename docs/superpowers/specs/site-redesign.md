# randy.dev — Full Redesign Spec
**Date:** 2026-04-05  
**Status:** Approved for implementation

---

## Overview

Complete redesign of randy.dev from a generic developer portfolio to a professional **PropTech / Real Estate AI Automation** portfolio. The visual direction is Bold Editorial × Dark Gold — heavy uppercase typography, gold line-art Rotterdam skyline, layered parallax background, and an AI/tech tone throughout the copy.

**Core pitch:** "I build AI tools that automate real estate workflows."

**Audience:** Dutch real estate professionals (brokers, developers, investors) — English as the professional signal, Dutch where it feels natural (about copy, status labels).

---

## Visual Design System

### Preserved (unchanged)
- Color palette: `#121110` bg, `#E8B931` gold, `#C49A1A` secondary gold, `#EDE8DC` text — all existing CSS variables stay
- Font stack: Space Grotesk (headings) + Source Serif 4 (body) — unchanged
- All CSS variable names — unchanged

### New typographic style
- Section headers: **ALL-CAPS, weight 900, letter-spacing -0.03em**, outline variant on the third line using `-webkit-text-stroke: 1px rgba(232,185,49,0.5)`
- Section eyebrows: monospace `font-family`, `SYS.PROFILE // OPERATOR` style labels with a glowing dot prefix
- Body copy: same as current but rewritten for RE/AI context
- Stat blocks: monospace numbers, bordered, no border-radius

### GlassCard
Removed entirely. Replaced with direct full-width section content using the bold editorial layout.

---

## Background Architecture (3 Parallax Layers)

All layers are `position: fixed`, `pointer-events: none`, stacked behind content at `zIndex: 0`.

| Layer | Component | Speed | Content |
|---|---|---|---|
| 1 (deepest) | `DataGrid` (new) | 0.05× scroll | Subtle CSS grid lines + monospace coordinate labels in corners |
| 2 (middle) | `CityskylineBackground` (new) | 0.15× scroll | Rotterdam gold line-art SVG, full-width, anchored to bottom |
| 3 (front) | `NetworkBackground` (existing) | 0.3× scroll (existing behavior) | Gold particle network canvas |

### CityskylineBackground — implementation detail
- New component: `src/components/CityskylineBackground.tsx`
- SVG paths trace a stylized Rotterdam skyline (Erasmus Bridge cables, Euromast tower, city blocks)
- On page load: **stroke-dashoffset draw-in animation** — lines draw themselves over ~2.5s with staggered delay per path group
- On scroll: `useScroll` + `useTransform` from Framer Motion, translates Y at 0.15× scroll speed
- Opacity: fixed at 0.3 (subtle, never competes with content)
- The existing vignette overlay in `layout.js` (top/bottom fade) stays — it naturally frames the skyline

### DataGrid — implementation detail
- New component: `src/components/DataGrid.tsx`
- Pure CSS: `background-image: linear-gradient(...)` repeating grid, 40px × 40px cells
- Corner labels: Amsterdam/Rotterdam coordinates in `font-family: monospace`, `color: rgba(232,185,49,0.15)`
- Parallax: `useScroll` + `useTransform`, translates Y upward at 0.05× scroll speed (e.g. scrollY 1000px → translateY -50px)

---

## Homepage (`src/app/page.js`) — Full Redesign

Scroll-snap structure preserved (`homepage-scroll` class, `snap-section`). 5 sections replacing the current 4.

### Section 1 — Hero (100vh)

**Animation on load:**
1. Rotterdam SVG draws itself in (handled by CityskylineBackground)
2. Eyebrow label fades in (delay 0.2s)
3. Headline lines stagger in from bottom, one by one (delay 0.4s, 0.1s stagger per line)
4. Subtext fades in (delay 0.8s)
5. CTA buttons slide up (delay 1.0s)

**Content:**
```
[glowing dot] REAL ESTATE × AI AUTOMATION
──────────────────────────────────────────
I BUILD AI TOOLS
THAT AUTOMATE
[outline] REAL ESTATE
WORKFLOWS.

From property document analysis to market intelligence —
I build the AI pipelines that save hours of manual work.

[CTA: VIEW PROJECTS →]  [CTA: ABOUT ME]
```

Navbar: Logo text changes from `randy.dev` to `RDG.` in `var(--accent-primary)` with `font-family: monospace`. Nav links get `letter-spacing: 0.08em` uppercase treatment. A "CONTACT" button with `border: 1px solid rgba(232,185,49,0.3)` replaces the current plain link.

### Section 2 — Capabilities (new)

Replaces the old "About preview" section.

**Eyebrow:** `MODULE_02 // CAPABILITIES`  
**Headline:** `WHAT I BUILD.`  
**Subline (outline):** `[outline text] FOR REAL ESTATE`

3 capability cards in a row, each with a gold left-border accent, icon, title, and 2-line description:

| Card | Title | Description |
|---|---|---|
| 1 (full gold border) | Document AI | RAG pipelines for lease contracts, valuations & due diligence docs |
| 2 | Market Intelligence | Automated data pipelines that surface pricing trends & insights |
| 3 | Workflow Automation | LLM-powered tools that automate repetitive broker & PM tasks |

**Animation:** `StaggerChildren` on the 3 cards, sliding in from bottom with 0.15s stagger.

### Section 3 — Projects

**Eyebrow:** `MODULE_03 // SYSTEMS`  
**Headline:** `BUILT PROJECTS.`

4 project rows (replacing the hover-panel layout):

| Project | Previous name | Status |
|---|---|---|
| Property Document AI | RAG Chatbot | Afgerond |
| RE Intelligence Dashboard | Personal Command Center | In ontwikkeling |
| Automated Valuation Model | *(new concept)* | Concept |
| randy.dev | randy.dev | Live |

Each row: title left, tag pills middle, status badge right. On hover: gold left-border animates in, row background shifts to `var(--bg-secondary)`.

**Animation:** `StaggerChildren` on rows, `AnimateIn direction="up"`.

### Section 4 — About Snippet

**Eyebrow:** `SYS.PROFILE // OPERATOR`  
**Headline (stacked):**
```
SELF-TAUGHT.
SYSTEMS-FOCUSED.
[outline] PROPTECH-DRIVEN.
```

Body: bilingual — English first ("I build AI systems that save real estate professionals hours of manual work."), Dutch second ("Geen buzzwords — alleen pipelines die draaien.").  
3 stat blocks (monospace, bordered): `4+ / Projects`, `RAG / Specialist`, `NL / Market`  
Link: `→ Full profile` to `/about`

### Section 5 — CTA (new)

Centered, minimal:
```
READY TO AUTOMATE?
Let's talk about what AI can do for your real estate workflow.
[GET IN TOUCH →]
```

---

## Inner Pages

### `/work` — Redesigned

- Same card layout but with new editorial header style
- **Eyebrow:** `SYS.INDEX // PROJECTS`
- Cards use the new bordered style (no border-radius, gold top-line on hover)
- Project descriptions rewritten for RE context (see content section below)
- New project added: Automated Valuation Model

### `/about` — Repositioned

- Bio rewritten: Randy as PropTech developer, not generic developer
- Tech stack section stays but adds RE-relevant tools (pandas, GeoPandas, property APIs)
- Add a "Currently exploring" subsection: AVM models, property data APIs, automated reporting

### `/blog` — Rewritten content

- 3 existing posts replaced with RE/AI topics:
  1. *"Building a Document AI for Dutch Lease Contracts"* — RAG for RE
  2. *"How AI is Changing Property Valuation in the Netherlands"* — market analysis angle  
  3. *"Claude Code as a PropTech Build Partner"* — keeps the dev tooling angle

---

## Content Rewrites

### Project: Property Document AI (was: RAG Chatbot)
**Description:** AI-powered document analysis for real estate professionals. Upload lease contracts, valuation reports, or due diligence packages — ask questions, get answers with source references.  
**Tags:** Python, LangChain, ChromaDB, OpenAI Embeddings  
**Features:** Hybrid search (semantic + keyword), conversation memory, source citations

### Project: RE Intelligence Dashboard (was: Personal Command Center)
**Description:** A real estate intelligence hub that aggregates market data, generates AI briefings, and surfaces actionable insights for property professionals.  
**Tags:** React, FastAPI, Claude API, Python  
**Features:** AI-generated market briefings, data aggregation, custom alerts

### Project: Automated Valuation Model (new)
**Description:** A machine learning pipeline that estimates property values using transaction data, location features, and market trends. Built on Dutch housing market data.  
**Tags:** Python, scikit-learn, pandas, FastAPI  
**Features:** Feature engineering pipeline, REST API endpoint, confidence intervals  
**Status:** Concept / In ontwikkeling

---

## New Components

| Component | File | Purpose |
|---|---|---|
| `CityskylineBackground` | `src/components/CityskylineBackground.tsx` | SVG Rotterdam skyline with draw-in + parallax |
| `DataGrid` | `src/components/DataGrid.tsx` | Subtle background grid with coordinate labels |

## Modified Components

| Component | Change |
|---|---|
| `Navbar.jsx` | Logo → `RDG.`, uppercase letter-spacing, contact button gold border |
| `Footer.jsx` | Match new editorial style |
| `layout.js` | Add `DataGrid` and `CityskylineBackground` alongside `NetworkBackground` |
| All pages | Remove `GlassCard` usage, apply new section/header patterns |

---

## Animation Summary

| Trigger | Element | Animation |
|---|---|---|
| Page load | Rotterdam SVG | stroke-dashoffset draw-in, 2.5s staggered per path |
| Page load | Hero headline | Lines stagger in from `y: 20`, opacity 0→1, 0.1s between lines |
| Page load | Hero CTA | Slide up, delay 1.0s |
| Scroll into view | Section headers | `AnimateIn direction="up"` (existing component) |
| Scroll into view | Capability cards | `StaggerChildren`, 0.15s stagger |
| Scroll into view | Project rows | `StaggerChildren`, 0.1s stagger |
| Scroll (continuous) | DataGrid | `useTransform` Y at 0.05× scroll |
| Scroll (continuous) | CityskylineBackground | `useTransform` Y at 0.15× scroll |
| Hover | Project rows | Gold left-border slides in, bg shifts |
| Hover | CTA button | Gold glow shadow, `translateY(-1px)` |

---

## Out of Scope

- No actual AVM model data (Automated Valuation Model is a concept card)
- No contact form functionality (CTA links to email)
- No blog post detail pages (existing behavior — posts link to `#`)
- No mobile-specific redesign (existing responsive behavior preserved)
