# Hero Scroll Timing, Photo Border & Navbar Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix hero scroll fade sequencing, add a blueprint-style photo border, and give the navbar a scroll-triggered materialization with vertical gold accent and SYS.ONLINE badge.

**Architecture:** Three independent tasks across two files. Task 1 splits the shared `heroOpacity` into separate `textOpacity`/`photoOpacity` MotionValues and wraps the scrim layers. Task 2 adds a decorative border strip as the last child of the hero section. Task 3 rewrites the navbar's scroll/visual logic without touching its routing or mobile overlay.

**Tech Stack:** Next.js 14 App Router, React 18, Framer Motion 12 (`useScroll`, `useTransform`), inline React styles with CSS variables.

---

### Task 1: Split scroll opacity in hero (`src/app/page.js`)

**Files:**
- Modify: `src/app/page.js`

**Context:** The hero currently uses a single `heroOpacity` MotionValue for both the text layer and the photo layer. This makes them fade simultaneously, which looks jarring. We need `textOpacity` (fast, 0–25% of hero height) and `photoOpacity` (delayed, 25%–85%) so text disappears first, then the photo follows.

The two scrim layers (Layer 1 gold tint, Layer 2 readability gradient) are cosmetically tied to the text and must also fade with it — wrap them together in a `motion.div` with `textOpacity`.

- [ ] **Step 1: Replace `heroOpacity` with two split MotionValues**

In `src/app/page.js`, find line 136:
```js
const heroOpacity  = useTransform(scrollY, [0, heroHeight * 0.6], [1, 0]);
```

Replace with:
```js
const textOpacity  = useTransform(scrollY, [0, heroHeight * 0.25], [1, 0]);
const photoOpacity = useTransform(scrollY, [heroHeight * 0.25, heroHeight * 0.85], [1, 0]);
```

- [ ] **Step 2: Apply `photoOpacity` to the photo wrapper**

Find line 183:
```jsx
<motion.div style={{ position: 'absolute', inset: 0, y: photoScrollY, opacity: heroOpacity }}>
```

Change `opacity: heroOpacity` to `opacity: photoOpacity`:
```jsx
<motion.div style={{ position: 'absolute', inset: 0, y: photoScrollY, opacity: photoOpacity }}>
```

- [ ] **Step 3: Wrap scrim layers in a `motion.div` with `textOpacity`**

Find the two scrim layer divs (Layer 1 and Layer 2). Currently they are two sibling divs:

```jsx
{/* Layer 1: Gold tint wash */}
<div
  aria-hidden="true"
  style={{
    position: 'absolute',
    inset: 0,
    background: 'linear-gradient(135deg, rgba(232,185,49,0.06) 0%, transparent 50%, rgba(232,185,49,0.03) 100%)',
    pointerEvents: 'none',
  }}
/>

{/* Layer 2: Readability gradient scrim */}
<div
  aria-hidden="true"
  style={{
    position: 'absolute',
    inset: 0,
    background: 'linear-gradient(90deg, rgba(12,10,8,0.88) 0%, rgba(12,10,8,0.72) 30%, rgba(12,10,8,0.22) 65%, transparent 100%)',
    pointerEvents: 'none',
    zIndex: 1,
  }}
/>
```

Replace both with a single `motion.div` wrapper containing them:

```jsx
{/* Layers 1 + 2: Scrim (fades with text) */}
<motion.div style={{ position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none', opacity: textOpacity }}>
  {/* Layer 1: Gold tint wash */}
  <div
    aria-hidden="true"
    style={{
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(135deg, rgba(232,185,49,0.06) 0%, transparent 50%, rgba(232,185,49,0.03) 100%)',
    }}
  />
  {/* Layer 2: Readability gradient scrim */}
  <div
    aria-hidden="true"
    style={{
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(90deg, rgba(12,10,8,0.88) 0%, rgba(12,10,8,0.72) 30%, rgba(12,10,8,0.22) 65%, transparent 100%)',
    }}
  />
</motion.div>
```

- [ ] **Step 4: Apply `textOpacity` to the text layer**

Find line 223:
```jsx
<motion.div style={{ position: 'relative', zIndex: 10, y: textScrollY, opacity: heroOpacity }}>
```

Change `opacity: heroOpacity` to `opacity: textOpacity`:
```jsx
<motion.div style={{ position: 'relative', zIndex: 10, y: textScrollY, opacity: textOpacity }}>
```

- [ ] **Step 5: Verify build passes**

```bash
npm run build
```

Expected: clean build, no errors about `heroOpacity` (it no longer exists).

- [ ] **Step 6: Visual check**

```bash
npm run dev
```

Open `http://localhost:3000`. Scroll slowly. Verify:
- Text and scrim disappear quickly (before you've scrolled far)
- A moment after the text is gone, the photo begins to fade
- Photo fully gone well before the capabilities section snaps in

- [ ] **Step 7: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): split scroll opacity — text fades fast, photo fades delayed"
```

---

### Task 2: Hero photo border strip (`src/app/page.js`)

**Files:**
- Modify: `src/app/page.js`

**Context:** Add a decorative strip at the bottom of the hero section — a blueprint grid combined with a diagonal ruler line, tick marks, corner marks, and a monospace label. The strip sits at `zIndex: 11` (above all layers) inside the hero `<section>` which has `overflow: hidden`. Since the strip is fully within the section bounds (72px from bottom), it will not be clipped.

- [ ] **Step 1: Add the border strip as the last child inside `<section>`**

Find the closing `</section>` tag of the hero section. It comes after the scroll indicator `motion.div`. Insert the following JSX immediately before `</section>`:

```jsx
{/* Hero border strip */}
<div
  aria-hidden="true"
  style={{
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    height: '72px',
    zIndex: 11,
    pointerEvents: 'none',
    overflow: 'hidden',
  }}
>
  {/* Blueprint grid */}
  <div style={{
    position: 'absolute',
    inset: 0,
    backgroundImage: `linear-gradient(${isDark ? 'rgba(232,185,49,0.10)' : 'rgba(232,185,49,0.18)'} 1px, transparent 1px), linear-gradient(90deg, ${isDark ? 'rgba(232,185,49,0.10)' : 'rgba(232,185,49,0.18)'} 1px, transparent 1px)`,
    backgroundSize: '20px 20px',
    WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 70%)',
    maskImage: 'linear-gradient(to bottom, transparent 0%, black 70%)',
  }} />

  {/* Diagonal ruler line */}
  <div style={{
    position: 'absolute',
    top: '16px', left: 0, right: 0,
    height: '1px',
    background: 'linear-gradient(90deg, transparent 0%, rgba(232,185,49,0.85) 8%, rgba(232,185,49,0.85) 92%, transparent 100%)',
    transform: 'rotate(-1deg)',
    transformOrigin: 'left center',
  }} />

  {/* Fine tick marks every 24px */}
  <div style={{
    position: 'absolute',
    top: '17px', left: 0, right: 0,
    height: '6px',
    background: 'repeating-linear-gradient(90deg, rgba(232,185,49,0.45) 0, rgba(232,185,49,0.45) 1px, transparent 1px, transparent 24px)',
  }} />

  {/* Major tick marks every 120px */}
  <div style={{
    position: 'absolute',
    top: '17px', left: 0, right: 0,
    height: '12px',
    background: 'repeating-linear-gradient(90deg, rgba(232,185,49,0.8) 0, rgba(232,185,49,0.8) 1px, transparent 1px, transparent 120px)',
  }} />

  {/* Corner mark — left */}
  <div style={{
    position: 'absolute',
    bottom: '8px', left: '16px',
    width: '8px', height: '8px',
    borderBottom: `1px solid ${isDark ? 'rgba(232,185,49,0.5)' : 'rgba(26,23,20,0.25)'}`,
    borderLeft: `1px solid ${isDark ? 'rgba(232,185,49,0.5)' : 'rgba(26,23,20,0.25)'}`,
  }} />

  {/* Corner mark — right */}
  <div style={{
    position: 'absolute',
    bottom: '8px', right: '16px',
    width: '8px', height: '8px',
    borderBottom: `1px solid ${isDark ? 'rgba(232,185,49,0.5)' : 'rgba(26,23,20,0.25)'}`,
    borderRight: `1px solid ${isDark ? 'rgba(232,185,49,0.5)' : 'rgba(26,23,20,0.25)'}`,
  }} />

  {/* Label */}
  <span style={{
    position: 'absolute',
    bottom: '10px', left: '32px',
    fontFamily: 'monospace',
    fontSize: '7px',
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    color: isDark ? 'rgba(232,185,49,0.35)' : 'rgba(26,23,20,0.25)',
  }}>
    // SYS.BOUNDARY_01
  </span>
</div>
```

- [ ] **Step 2: Verify build passes**

```bash
npm run build
```

Expected: clean build.

- [ ] **Step 3: Visual check — dark mode**

```bash
npm run dev
```

Open `http://localhost:3000` in dark mode. At the bottom of the hero section, verify:
- A blueprint grid fades in from the bottom
- A diagonal gold ruler line with tick marks sits at the top of the strip
- Corner marks visible bottom-left and bottom-right
- `// SYS.BOUNDARY_01` label visible in gold

- [ ] **Step 4: Visual check — light mode**

Toggle to light mode. Verify the grid, corner marks, and label are visible (slightly darker tone on the warm white background).

- [ ] **Step 5: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): add blueprint grid border strip with diagonal ruler line"
```

---

### Task 3: Navbar scroll-triggered redesign (`src/components/Navbar.jsx`)

**Files:**
- Modify: `src/components/Navbar.jsx`

**Context:** The navbar needs to be transparent when at the top of the page and gain visual weight (blur, background, border, vertical accent line, SYS.ONLINE badge) once the user scrolls past 40px. `useTheme` is not currently imported in `Navbar.jsx` — add it. The mobile overlay is unaffected.

- [ ] **Step 1: Add `useTheme` import**

Find line 7 in `src/components/Navbar.jsx`:
```js
import ThemeToggle from './ThemeToggle';
```

Add after it:
```js
import { useTheme } from './ThemeProvider';
```

- [ ] **Step 2: Add scroll state and `isDark` inside the component**

Find the existing state declarations at the top of the `Navbar` function (around line 19):
```js
const [menuOpen, setMenuOpen] = useState(false);
const [hoveredHref, setHoveredHref] = useState(null);
```

Add after them:
```js
const [scrolled, setScrolled] = useState(false);
const { theme } = useTheme();
const isDark = theme === 'dark';
```

- [ ] **Step 3: Add scroll detection effect**

Find the existing `useEffect` blocks (around lines 22–27). Add a new `useEffect` after them:

```js
useEffect(() => {
  const onScroll = () => setScrolled(window.scrollY > 40);
  window.addEventListener('scroll', onScroll, { passive: true });
  return () => window.removeEventListener('scroll', onScroll);
}, []);
```

- [ ] **Step 4: Replace the static header styles with scroll-conditional styles**

Find the `<motion.header>` element (around line 43). Its current `style` prop is:

```js
style={{
  position: 'sticky',
  top: 0,
  zIndex: 100,
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  backgroundColor: 'color-mix(in srgb, var(--bg-primary) 85%, transparent)',
  borderBottom: '1px solid rgba(232,185,49,0.08)',
}}
```

Replace the entire `style` prop with:

```js
style={{
  position: 'sticky',
  top: 0,
  zIndex: 100,
  transition: 'background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, backdrop-filter 0.3s ease',
  backdropFilter: scrolled ? 'blur(16px)' : 'none',
  WebkitBackdropFilter: scrolled ? 'blur(16px)' : 'none',
  backgroundColor: scrolled
    ? (isDark ? 'rgba(18,17,16,0.82)' : 'rgba(251,248,240,0.88)')
    : 'transparent',
  borderBottom: scrolled
    ? '1px solid rgba(232,185,49,0.15)'
    : '1px solid transparent',
  boxShadow: scrolled
    ? (isDark ? '0 1px 32px rgba(0,0,0,0.5)' : '0 1px 20px rgba(26,23,20,0.08)')
    : 'none',
}}
```

- [ ] **Step 5: Add the vertical gold accent line inside the header**

Find the `<div className="container" ...>` that is the first child of `<motion.header>`. Add a `<div>` as the very first child inside `<motion.header>`, before the container div:

```jsx
{/* Vertical gold accent line */}
<div
  aria-hidden="true"
  style={{
    position: 'absolute',
    left: 0, top: '6px', bottom: '6px',
    width: '2px',
    background: 'linear-gradient(to bottom, transparent, #E8B931 35%, #E8B931 65%, transparent)',
    opacity: scrolled ? 1 : 0,
    transition: 'opacity 0.3s ease',
    pointerEvents: 'none',
  }}
/>
```

- [ ] **Step 6: Add `paddingLeft` to the logo**

Find the logo `<Link>` (around line 62):
```jsx
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
```

Add `paddingLeft: '12px'` to its style:
```jsx
<Link
  href="/"
  style={{
    fontFamily: 'monospace',
    fontWeight: 700,
    fontSize: 'var(--text-lg)',
    color: 'var(--accent-primary)',
    letterSpacing: '0.05em',
    textDecoration: 'none',
    paddingLeft: '12px',
  }}
>
```

- [ ] **Step 7: Add the SYS.ONLINE badge in the desktop nav**

Find the desktop `<nav>` (around line 77). Inside the `<LayoutGroup>` block, after the closing `</LayoutGroup>` tag and before the CONTACT `<a>` tag, add:

```jsx
{/* SYS.ONLINE badge */}
<div style={{
  display: 'flex', alignItems: 'center', gap: '5px',
  fontFamily: 'monospace', fontSize: '8px', letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: isDark ? 'rgba(232,185,49,0.3)' : 'rgba(26,23,20,0.25)',
  opacity: scrolled ? 1 : 0,
  transition: 'opacity 0.4s ease',
  userSelect: 'none',
}}>
  <span style={{
    width: 5, height: 5, borderRadius: '50%',
    backgroundColor: 'rgba(34,197,94,0.85)',
    boxShadow: '0 0 6px rgba(34,197,94,0.5)',
    display: 'inline-block', flexShrink: 0,
  }} />
  SYS.ONLINE
</div>
```

- [ ] **Step 8: Verify build passes**

```bash
npm run build
```

Expected: clean build.

- [ ] **Step 9: Visual check — dark mode**

```bash
npm run dev
```

Open `http://localhost:3000` in dark mode. Verify:
- At the very top: navbar is fully transparent (hero photo visible behind it)
- Scroll down 50px: navbar gains blur, dark background, gold border-bottom
- Vertical gold accent line appears on the left edge
- `SYS.ONLINE` badge with green pulse dot fades in between nav links and CONTACT
- Toggle back to top: navbar returns to transparent smoothly

- [ ] **Step 10: Visual check — light mode**

Toggle to light mode. Verify:
- At top: transparent (warm white page background shows through)
- After scroll: warm semi-opaque background (`rgba(251,248,240,0.88)`), subtle shadow, gold border

- [ ] **Step 11: Commit**

```bash
git add src/components/Navbar.jsx
git commit -m "feat(navbar): scroll-triggered materialization with gold accent line and SYS.ONLINE badge"
```
