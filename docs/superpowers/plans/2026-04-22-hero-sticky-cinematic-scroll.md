# Hero Sticky Cinematic Scroll — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the scrollY-pixel-based hero animation with a sticky 200vh cinematic sequence — text+scrim dissolve together, photo "moment", then photo surges upward and disappears.

**Architecture:** A 200vh wrapper div wraps the hero section. The hero uses `position: sticky; top: 0; height: 100vh` so it locks in the viewport while the user scrolls through the wrapper. All animation transforms are driven by `useScroll({ target: wrapperRef, offset: ['start start', 'end end'] })` which returns a normalized `scrollYProgress` (0→1).

**Tech Stack:** Next.js 14, React 18, Framer Motion 12 (`useScroll`, `useTransform`, `motion.div`)

---

### Task 1: Replace scroll hook and remove pixel-based transforms

**Files:**
- Modify: `src/app/page.js`

The current code uses `useScroll()` (global scroll) and a complex `photoScrollY` transform that adds positive px to counteract section movement. This whole approach is replaced by sticky positioning + a normalized progress value.

- [ ] **Step 1: Add `wrapperRef` and replace the scroll hook**

In `src/app/page.js`, find the top of the `Page` component (around line 127). Replace:

```js
const photoRef = useRef(null);
const textRef  = useRef(null);
const { theme } = useTheme();
const isDark = theme === 'dark';

const { scrollY } = useScroll();
const heroHeight = typeof window !== 'undefined' ? window.innerHeight : 800;

// Phase 1: text drifts up and fades      (0% → 18% of hero height)
// Phase 2: hold — nothing animates       (18% → 45%)
// Phase 3: scrim dissolves               (45% → 75%)
// Phase 4: photo revealed, holds still   (45% → 88%) — scrim gone at 75%
// Phase 5: photo surges upward           (88% → 100%)
//
// photoScrollY uses px to counteract the section scrolling up.
// y = +scrollY keeps photo fixed in viewport; reducing y in phase 5 lets it rise.
const hh = heroHeight;
const photoScrollY = useTransform(
  scrollY,
  [0,  hh * 0.88,  hh],
  [0,  hh * 0.88,  hh * 0.82]
);
const textScrollY  = useTransform(scrollY, [0,                 heroHeight * 0.22], ['0%', '-5%']);
const textOpacity  = useTransform(scrollY, [0,                 heroHeight * 0.18], [1, 0]);
const scrimOpacity = useTransform(scrollY, [heroHeight * 0.45, heroHeight * 0.75], [1, 0]);
```

With:

```js
const photoRef   = useRef(null);
const textRef    = useRef(null);
const wrapperRef = useRef(null);
const { theme } = useTheme();
const isDark = theme === 'dark';

// scrollYProgress runs 0→1 over the 200vh wrapper.
// Sticky positioning keeps the hero fixed — no px-offset hacks needed.
const { scrollYProgress } = useScroll({
  target: wrapperRef,
  offset: ['start start', 'end end'],
});

// Act 1 (0–0.30): text + scrim dissolve together; indicator leaves first
// Act 2 (0.30–0.75): everything holds — full photo visible, mouse parallax active
// Act 3 (0.75–1.00): photo surges up and hard-fades out
const indicatorOpacity = useTransform(scrollYProgress, [0, 0.20], [1, 0]);
const textOpacity      = useTransform(scrollYProgress, [0, 0.30], [1, 0]);
const textY            = useTransform(scrollYProgress, [0, 0.30], ['0%', '-4%']);
const scrimOpacity     = useTransform(scrollYProgress, [0, 0.30], [1, 0]);
const photoY           = useTransform(scrollYProgress, [0.75, 1.0], ['0%', '-120%']);
const photoOpacity     = useTransform(scrollYProgress, [0.75, 1.0], [1, 0]);
```

- [ ] **Step 2: Verify the dev server still compiles**

```bash
npm run dev
```

Expected: no errors in terminal and no red overlay in browser. The hero may look broken at this point — that is expected, the JSX hasn't been updated yet.

---

### Task 2: Wrap hero section in 200vh sticky wrapper

**Files:**
- Modify: `src/app/page.js`

The hero `<section>` currently sits directly inside the scroll-snap container. It needs a 200vh wrapper outside of it, and its own styles need to change to `position: sticky`.

- [ ] **Step 1: Add the wrapper and update the section styles**

Find the hero section opening tag (around line 183):

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
```

Replace with:

```jsx
      <div
        ref={wrapperRef}
        style={{ height: '200vh', scrollSnapAlign: 'start' }}
      >
      <section
        onMouseMove={handleHeroMouseMove}
        onMouseLeave={handleHeroMouseLeave}
        style={{
          position: 'sticky',
          top: 0,
          height: '100vh',
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
```

Note: `className="snap-section"` is removed from the section — the wrapper takes the snap role. `minHeight: 'unset'` is no longer needed since we're using a fixed `height: '100vh'`.

- [ ] **Step 2: Close the wrapper div after the section**

Find the closing tag of the hero section (the `</section>` right before `<div style={{ height: '45vh' }} />`). After it, add the closing wrapper div:

```jsx
      </section>
      </div>
```

- [ ] **Step 3: Start dev server and verify the hero is sticky**

```bash
npm run dev
```

Open `http://localhost:3000`. Scroll slowly. Expected: the hero content stays locked in the viewport while you scroll through extra space. The animations won't work yet (photo still broken) — that's fine.

---

### Task 3: Wire up photo, scrim, text, and indicator to new transforms

**Files:**
- Modify: `src/app/page.js`

Now connect all the `motion.div` elements to the new transform values.

- [ ] **Step 1: Update the photo layer**

Find (around line 199):

```jsx
        {/* Layer 0: Photo */}
        <motion.div style={{ position: 'absolute', inset: 0, y: photoScrollY }}>
```

Replace with:

```jsx
        {/* Layer 0: Photo */}
        <motion.div style={{ position: 'absolute', inset: 0, y: photoY, opacity: photoOpacity }}>
```

- [ ] **Step 2: Update the scrim layer**

Find (around line 216):

```jsx
        <motion.div style={{ position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none', opacity: scrimOpacity }}>
```

This line already uses `scrimOpacity` — no change needed. The variable name is the same; only its definition changed in Task 1. ✓

- [ ] **Step 3: Update the text layer**

Find (around line 238):

```jsx
        <motion.div style={{ position: 'relative', zIndex: 10, y: textScrollY, opacity: textOpacity }}>
```

Replace with:

```jsx
        <motion.div style={{ position: 'relative', zIndex: 10, y: textY, opacity: textOpacity }}>
```

- [ ] **Step 4: Update the scroll indicator**

Find the scroll indicator `motion.div` (around line 354):

```jsx
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
```

Replace with:

```jsx
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
            opacity: indicatorOpacity,
          }}
        >
```

Note: `initial={{ opacity: 0 }}` and `animate={{ opacity: 1 }}` handle the entrance animation; `style={{ opacity: indicatorOpacity }}` drives the scroll-out. Framer Motion composes these correctly.

- [ ] **Step 5: Verify full animation in browser**

```bash
npm run dev
```

Open `http://localhost:3000`. Test the full scroll sequence:
1. Page loads → hero appears with text + scrim ✓
2. Start scrolling → scroll indicator fades (first), then text + scrim dissolve together ✓
3. Continue scrolling → full photo visible, no text, no scrim, mouse parallax active ✓
4. Scroll further → photo shoots upward and hard-fades out ✓
5. Next section (capabilities) snaps into view ✓

- [ ] **Step 6: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): sticky cinematic scroll — text+scrim dissolve, photo moment, surge exit"
```

---

### Task 4: Verify build and no regressions

**Files:**
- No changes

- [ ] **Step 1: Run production build**

```bash
npm run build
```

Expected: exits with `✓ Compiled successfully`. No TypeScript errors, no missing module errors.

- [ ] **Step 2: Smoke-test all pages**

```bash
npm run dev
```

Visit each route and confirm no visual regressions:
- `http://localhost:3000` — hero animation ✓, capabilities section ✓, projects ✓, about snippet ✓, CTA ✓
- `http://localhost:3000/work` — page loads and renders correctly ✓
- `http://localhost:3000/about` — page loads and renders correctly ✓
- `http://localhost:3000/blog` — page loads and renders correctly ✓

- [ ] **Step 3: Check dark/light theme**

Toggle theme on the homepage. Confirm:
- Photo brightness filter changes correctly ✓
- Blueprint grid tint colors correct ✓
- Corner marks correct ✓
