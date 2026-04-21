# Hero Scroll Timing, Photo Border & Navbar Redesign — Design Spec

**Date:** 2026-04-21  
**Files affected:** `src/app/page.js`, `src/components/Navbar.jsx`  
**Status:** Approved

---

## Problem

1. Text and photo fade at the same rate — the photo fading while text is still visible looks jarring.
2. The hero has no visual boundary between it and the next section.
3. The navbar looks minimal and doesn't change on scroll; it lacks visual presence.

---

## Solution Overview

Four targeted changes across two files:

1. **Split scroll opacity** — text fades fast, photo fades only after text is gone.
2. **Hero photo border** — blueprint grid strip + diagonal ruler line at the bottom of the hero.
3. **Navbar scroll-triggered materialization** — transparent at top, gains visual weight on scroll.
4. **Navbar style upgrade** — vertical gold left-accent line + SYS.ONLINE badge (materializes with scroll).

---

## 1. Split Scroll Opacity (`src/app/page.js`)

Replace the single `heroOpacity` MotionValue with two separate ones.

**Remove:**
```js
const heroOpacity = useTransform(scrollY, [0, heroHeight * 0.6], [1, 0]);
```

**Add:**
```js
// Text + scrim: fade fast (0 → 25% of hero height)
const textOpacity  = useTransform(scrollY, [0, heroHeight * 0.25], [1, 0]);
// Photo: delayed fade (25% → 85% of hero height)
const photoOpacity = useTransform(scrollY, [heroHeight * 0.25, heroHeight * 0.85], [1, 0]);
```

Apply:
- `textOpacity` → text wrapper `motion.div` (Layer 3)
- `photoOpacity` → photo wrapper `motion.div` (Layer 0)

The gradient scrim layers (Layer 1 gold tint, Layer 2 readability scrim) also get `textOpacity` applied — they are cosmetically tied to the text side and should disappear with it. Wrap both scrim divs in a single `motion.div` with `opacity: textOpacity`.

---

## 2. Hero Photo Border (`src/app/page.js`)

An absolutely-positioned strip at the `bottom: 0` of the hero `<section>`. It sits at `zIndex: 11` (above photo, scrim, and text layers).

### Structure

```
<div> (outer strip, position: absolute, bottom: 0, left: 0, right: 0, height: 72px, zIndex: 11, pointerEvents: none)
  ├── Grid layer (blueprint raster)
  ├── Diagonal ruler line
  ├── Tick marks (repeating gradient)
  ├── Corner marks (left + right)
  └── Monospace label
```

### Grid layer

```css
background-image:
  linear-gradient(rgba(232,185,49,0.10) 1px, transparent 1px),
  linear-gradient(90deg, rgba(232,185,49,0.10) 1px, transparent 1px);
background-size: 20px 20px;
mask-image: linear-gradient(to bottom, transparent 0%, black 70%);
```

Light mode: replace `rgba(232,185,49,0.10)` with `rgba(232,185,49,0.18)` (slightly stronger on light bg).

### Diagonal ruler line

A `div` at the top of the strip with:
```css
height: 1px;
background: linear-gradient(90deg, transparent 0%, rgba(232,185,49,0.85) 8%, rgba(232,185,49,0.85) 92%, transparent 100%);
transform: rotate(-1deg);
transform-origin: left center;
```

### Tick marks

Two layers via `repeating-linear-gradient`:
- Fine ticks: every `24px`, height `6px`, opacity 0.45
- Major ticks: every `120px`, height `12px`, opacity 0.8

Both sit just below the diagonal line.

### Corner marks

Two `div`s at `bottom: 8px`:
- Left: `border-bottom + border-left`, `8×8px`, `rgba(232,185,49,0.5)`
- Right: `border-bottom + border-right`, same

### Label

```jsx
<span style={{
  fontFamily: 'monospace',
  fontSize: '7px',
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'rgba(232,185,49,0.35)',
  position: 'absolute',
  bottom: '10px',
  left: '24px',
}}>
  // SYS.BOUNDARY_01
</span>
```

Light mode: `rgba(26,23,20,0.25)` for label and corner marks.

---

## 3 & 4. Navbar Redesign (`src/components/Navbar.jsx`)

### Scroll detection

Add `useEffect` + `useState` to track whether the page has scrolled past 40px:

```js
const [scrolled, setScrolled] = useState(false);

useEffect(() => {
  const onScroll = () => setScrolled(window.scrollY > 40);
  window.addEventListener('scroll', onScroll, { passive: true });
  return () => window.removeEventListener('scroll', onScroll);
}, []);
```

### Visual states

Remove the existing `backgroundColor: 'color-mix(in srgb, var(--bg-primary) 85%, transparent)'` and `borderBottom: '1px solid rgba(232,185,49,0.08)'` from the header's static style. Replace with the scroll-conditional values below.

Both states share `transition: 'background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, backdrop-filter 0.3s ease'` on the `<motion.header>`.

**At top (`!scrolled`):**
```js
backgroundColor: 'transparent'
backdropFilter: 'none'
borderBottom: '1px solid transparent'
boxShadow: 'none'
```

**After scroll (`scrolled`):**
```js
// dark mode
backgroundColor: 'rgba(18,17,16,0.82)'
// light mode
backgroundColor: 'rgba(251,248,240,0.88)'

backdropFilter: 'blur(16px)'
WebkitBackdropFilter: 'blur(16px)'
borderBottom: '1px solid rgba(232,185,49,0.15)'
boxShadow: isDark
  ? '0 1px 32px rgba(0,0,0,0.5)'
  : '0 1px 20px rgba(26,23,20,0.08)'
```

### Vertical gold left-accent line

A `div` inside `<motion.header>` at `position: absolute, left: 0, top: 6px, bottom: 6px, width: 2px`:

```js
background: 'linear-gradient(to bottom, transparent, #E8B931 35%, #E8B931 65%, transparent)'
opacity: scrolled ? 1 : 0
transition: 'opacity 0.3s ease'
```

### SYS.ONLINE badge

Add between the nav links and the CONTACT button on desktop:

```jsx
<div style={{
  display: 'flex', alignItems: 'center', gap: '5px',
  fontFamily: 'monospace', fontSize: '8px', letterSpacing: '0.12em',
  color: isDark ? 'rgba(232,185,49,0.3)' : 'rgba(26,23,20,0.25)',
  textTransform: 'uppercase',
  opacity: scrolled ? 1 : 0,
  transition: 'opacity 0.4s ease',
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

The badge is hidden (`opacity: 0`) when not scrolled and fades in when scrolled. Desktop only — omit from mobile overlay.

### Logo padding

Add `paddingLeft: '12px'` to the logo link to visually clear the vertical accent line.

---

## Constraints

- No new dependencies.
- All styles remain inline React style objects using CSS variables where possible.
- Mobile overlay menu is unaffected by navbar style changes (no vertical line, no SYS.ONLINE badge).
- The `useTheme` hook is already used in `page.js`; `Navbar.jsx` does **not** currently use it. Add `useTheme` import + `const { theme } = useTheme(); const isDark = theme === 'dark';` to `Navbar.jsx`.

---

## Files Changed

| File | Change |
|------|--------|
| `src/app/page.js` | Split heroOpacity into textOpacity + photoOpacity; wrap scrim layers; add hero border strip |
| `src/components/Navbar.jsx` | Add scroll detection, scroll-triggered visual state, vertical accent line, SYS.ONLINE badge, useTheme |
