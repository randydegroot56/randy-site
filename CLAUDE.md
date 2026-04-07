# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev      # Start development server (localhost:3000)
npm run build    # Production build — run this to verify no errors after changes
npm run start    # Start production server
```

No lint or test scripts are configured.

---

## Architecture

**randy.dev** is a Next.js 14.2 portfolio site (App Router, `src/app/`) using React 18 and Framer Motion 12. All content is hardcoded — no CMS, no API calls, no database.

### Routing

| Route | File | Description |
|---|---|---|
| `/` | `src/app/page.js` | Homepage with scroll-snap sections (hero → about preview → projects → blog) |
| `/work` | `src/app/work/page.js` | Full project cards with feature lists |
| `/about` | `src/app/about/page.js` | Two-column bio + tech stack |
| `/blog` | `src/app/blog/page.js` | Blog post listing |

### File structure

```
src/
  app/
    layout.js          ← Root layout: ThemeProvider, NetworkBackground, vignette, Navbar, Footer
    page.js            ← Homepage (GlassCard component lives here, not shared)
    about/page.js
    work/page.js
    blog/page.js
  components/
    ThemeProvider.jsx  ← Context + useTheme() hook
    ThemeToggle.jsx    ← Sun/moon button
    Navbar.jsx         ← Sticky header, animated underline, mobile overlay
    Footer.jsx         ← Logo + links + copyright
    AnimateIn.jsx      ← Scroll-triggered directional fade
    StaggerChildren.jsx← Staggered child entrance
    PageTransition.jsx ← Route-change slide animation
    NetworkBackground.tsx ← Canvas 3D particle network (only .tsx file in project)
    ParallaxBackground.jsx ← Framer Motion parallax wrapper
  styles/
    globals.css        ← Design system: ALL CSS variables, reset, snap-scroll rules
```

**Duplicate root files** (`layout.js`, `page.js`, `globals.css`, `ThemeProvider.jsx`, `ThemeToggle.jsx`) exist at the project root — ignore them. The authoritative files are in `src/`.

---

## Design System

Everything lives in `src/styles/globals.css`. Never hardcode color values or spacing numbers — always use the variables below.

### Colors

Both themes share the same accent palette. Background and text vary.

```css
/* Accent — identical in light and dark */
--accent-primary:       #E8B931   /* gold, used for highlights, CTAs, active states */
--accent-primary-hover: #D4A620   /* darker gold on hover */
--accent-secondary:     #C49A1A   /* subdued gold, labels, links, CTA text */
--accent-tertiary:      #8A6C10   /* darkest gold, rarely used */

/* Light theme */
--bg-primary:    #FBF8F0   /* page background (warm white) */
--bg-secondary:  #F0EADB   /* subtle surface (hover backgrounds, inputs) */
--bg-elevated:   #FFFFFF   /* cards, modals, elevated surfaces */
--text-primary:  #1A1714   /* main body text */
--text-secondary:#6B5E4A   /* secondary copy, descriptions */
--text-muted:    #9C8E72   /* meta, timestamps, labels */
--surface-card:  #FFFFFF
--border-subtle: rgba(26,23,20,0.08)
--border-default:rgba(26,23,20,0.15)

/* Dark theme */
--bg-primary:    #121110
--bg-secondary:  #2A2622
--bg-elevated:   #3A3530
--text-primary:  #EDE8DC
--text-secondary:#8A8279
--text-muted:    #5E5850
--surface-card:  #2A2622
--border-subtle: rgba(237,232,220,0.06)
--border-default:rgba(237,232,220,0.12)
```

**Shadows** — all warm-tinted:
```css
--shadow-sm   /* 1px lift */
--shadow-md   /* 4px card */
--shadow-lg   /* 10px modal */
--shadow-glow /* gold glow: 0 0 20px rgba(232,185,49,0.35..0.4) */
```

### Typography

```css
--font-heading: 'Space Grotesk', system-ui, sans-serif   /* UI text, labels, buttons, headings */
--font-body:    'Source Serif 4', Georgia, serif          /* body: set on <body> in globals.css */

/* Scale (Major Third 1.25×) */
--text-xs:   0.75rem   /* 12px — labels, tags, meta */
--text-sm:   0.875rem  /* 14px — secondary text, captions */
--text-base: 1rem      /* 16px — body default */
--text-md:   1.125rem  /* 18px — lead paragraphs */
--text-lg:   1.25rem   /* 20px — card titles */
--text-xl:   1.5625rem /* 25px — section subtitles */
--text-2xl:  1.953rem  /* ~31px — section headings */
--text-3xl:  2.441rem  /* ~39px — page titles */
--text-4xl:  3.052rem  /* ~49px — hero heading */
```

Rule: headings always use `fontFamily: 'var(--font-heading)'`. Body copy inherits `var(--font-body)` from the `<body>` element.

### Spacing

```css
--space-1: 0.25rem (4px)    --space-8:  2rem (32px)
--space-2: 0.5rem  (8px)    --space-10: 2.5rem (40px)
--space-3: 0.75rem (12px)   --space-12: 3rem (48px)
--space-4: 1rem    (16px)   --space-16: 4rem (64px)
--space-5: 1.25rem (20px)   --space-20: 5rem (80px)
--space-6: 1.5rem  (24px)   --space-24: 6rem (96px)
                             --space-32: 8rem (128px)
```

### Border radius

```css
--radius-sm:   0.25rem (4px)    --radius-xl:   1rem (16px)
--radius-md:   0.5rem  (8px)    --radius-2xl:  1.5rem (24px)
--radius-lg:   0.75rem (12px)   --radius-full: 9999px
```

### Transitions

```css
--transition-fast: 150ms ease   /* hover color changes */
--transition-base: 250ms ease   /* background, border, layout */
--transition-slow: 400ms ease   /* larger state changes */
```

---

## Styling Rules

**All styles are inline React style objects referencing CSS variables.** There is no CSS framework, no CSS Modules, no styled-components.

```jsx
// Correct
<h2 style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)', fontSize: 'var(--text-2xl)' }}>

// Wrong — never hardcode values
<h2 style={{ fontFamily: 'Space Grotesk', color: '#1A1714', fontSize: '31px' }}>
```

**Theme-aware inline styles** require `useTheme()`:

```jsx
const { theme } = useTheme();
const isDark = theme === 'dark';
// Then branch:
backgroundColor: isDark ? 'rgba(42,38,34,0.06)' : 'rgba(240,234,219,0.08)'
```

**Hover on regular elements** — use `onMouseEnter`/`onMouseLeave` with `e.currentTarget.style.*`:

```jsx
onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
onMouseLeave={e => { e.currentTarget.style.color = 'var(--accent-secondary)'; }}
```

**Hover on Framer Motion elements** — use `whileHover` prop:

```jsx
<motion.article whileHover={{ y: -6, boxShadow: 'var(--shadow-glow)', borderColor: 'var(--accent-primary)' }} />
```

---

## Theming

`ThemeProvider` wraps the entire app in `layout.js`. It:
- Sets `data-theme="light|dark"` on `<html>`
- Persists choice to `localStorage`
- Falls back to `prefers-color-scheme`

**To access theme in any client component:**

```jsx
import { useTheme } from '../components/ThemeProvider';
const { theme, toggleTheme } = useTheme();
```

Every client component that reads the theme must be inside `ThemeProvider` (all page components are, since layout wraps them).

---

## Animation Components

### AnimateIn

Scroll-triggered directional fade-in. Triggers once when entering the viewport.

```jsx
<AnimateIn direction="left" delay={0.1}>
  <YourContent />
</AnimateIn>
```

Props: `direction` ('up' | 'down' | 'left' | 'right', default: 'up'), `delay` (seconds, default: 0).  
Animation: 30px offset → 0, opacity 0 → 1, 0.6s easeOut. Viewport margin: -50px.

### StaggerChildren

Wraps a list; each child fades in with a 0.1s delay between items.

```jsx
<StaggerChildren style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
  <div>Item 1</div>
  <div>Item 2</div>
</StaggerChildren>
```

Props: `style` (applied to the container div). Animation: opacity 0 → 1, y 20 → 0, 0.5s easeOut per child.

### PageTransition

Already applied in `layout.js` — wraps all page content. Slides new pages in from the right, exits to the left, 0.4s with cubic ease `[0.22, 1, 0.36, 1]`.

### AnimatePresence (Framer Motion)

Use for conditionally rendered elements (side panels, modals, overlays):

```jsx
import { AnimatePresence, motion } from 'framer-motion';

<AnimatePresence mode="wait">
  {condition && (
    <motion.div
      key={uniqueKey}
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 12 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
    >
      ...
    </motion.div>
  )}
</AnimatePresence>
```

---

## Layout Patterns

### Homepage scroll-snap

The homepage wraps everything in `<div className="homepage-scroll">`. This activates `scroll-snap-type: y proximity` (defined in globals.css via `html:has(.homepage-scroll)`).

Each snap section uses `className="snap-section"` which provides:
- `min-height: 100vh`
- `display: flex; flex-direction: column; justify-content: center`
- `padding: var(--space-20) 0`
- `position: relative` ← important for absolutely-positioned children
- `scroll-snap-align: center`

### GlassCard (homepage only)

`GlassCard` is a local component in `src/app/page.js` (not shared). It renders the frosted-glass content panels.

Key styles:
- `width: 50%`, `marginLeft: var(--space-12)` — left-aligned at 50% width
- `padding: var(--space-10) var(--space-16)`
- `backdropFilter: blur(40px)`
- Gold left-line: `background: linear-gradient(to right, transparent 6px, var(--accent-primary) 6px, var(--accent-primary) 8px, transparent 8px), <fill>`
- Scroll-based opacity fade via `useScroll` + `useTransform` (thresholds: 0→fade in at 10%, fade out at 90%→1)
- `variant="hero"` overrides to full-width, no margin, no padding (content in inner `.container` div handles its own padding)

**Hover side panels** (projects + blog sections) are positioned absolute at `left: calc(50% + var(--space-16))` relative to a `position: relative` wrapper div that contains both the AnimateIn/GlassCard and the panel.

### Container

Use `className="container"` for full-width sections that need centered, padded content:
- `max-width: 1200px`, `margin-inline: auto`, `padding-inline: var(--space-6)`

### Non-homepage pages

Use a `<section>` with `minHeight: '100vh'`, `display: 'flex'`, `alignItems: 'center'`, `justifyContent: 'center'`, `padding: 'var(--space-20) var(--space-6)'`. Content inside a `<div>` with `maxWidth` (720px for single-column, 960px for two-column).

---

## Component Patterns

### Data at the top

All hardcoded data (projects, posts, stack items) is defined as `const` arrays at the top of the file, before the component.

```js
const projects = [
  { title: '...', description: '...', tags: [...], status: '...', statusStyle: {...} },
];
```

### Status badges

Project cards use `statusStyle` objects alongside the status string:

```js
statusStyle: {
  bg:     'rgba(34, 197, 94, 0.12)',    // completed = green
  border: 'rgba(34, 197, 94, 0.28)',
  text:   'rgba(34, 197, 94, 0.95)',
  dot:    'rgba(34, 197, 94, 0.9)',
}
// In-progress / Live = amber (accent-primary values)
```

### Navbar active state

`isActive(href)` returns true when `pathname === href` (for `/`) or `pathname.startsWith(href)` (for other routes). Active links show a gold `motion.span` with `layoutId="nav-underline"` that slides between links.

### 'use client'

Every component and page file starts with `'use client'`. There are no server components in use.

---

## NetworkBackground

`NetworkBackground.tsx` (the only TypeScript file) renders a fixed-position canvas behind everything. It is configured in `layout.js`:

```jsx
<NetworkBackground nodeColor="#E8B931" pulseColor="#C49A1A" bgColor="transparent" />
```

Do not change the canvas rendering logic without careful testing — it is complex and visually sensitive. The canvas sits at `zIndex: 0`; the vignette overlay sits at `zIndex: 5` (defined in `layout.js`); content starts at `zIndex: 1+`.

**Fixed vignette** in `layout.js`:
```jsx
<div aria-hidden="true" style={{
  position: 'fixed', inset: 0, zIndex: 5, pointerEvents: 'none',
  background: 'linear-gradient(to bottom, var(--bg-primary) 0%, transparent 10%, transparent 90%, var(--bg-primary) 100%)',
}} />
```
This fades the top and bottom 10% of the viewport into the background color.

---

## Adding New Content

**New page** (`/example`):
1. Create `src/app/example/page.js`
2. Start with `'use client'`
3. Use the non-homepage section pattern: full-height section, `.container` or maxWidth div, `AnimateIn`/`StaggerChildren` for entrance
4. Use only CSS variables for all colors/spacing

**New homepage section**:
1. Add a `<section className="snap-section">` with a `<div style={{ position: 'relative' }}>` wrapper inside
2. Wrap content in `<AnimateIn>` and `<GlassCard>`
3. Add a `<div style={{ height: '45vh' }} />` spacer before it

**New project or blog post**:
- Add an entry to the `projects` or `latestPosts` array in `src/app/page.js` and the matching `projects` / `posts` array in `src/app/work/page.js` or `src/app/blog/page.js`
