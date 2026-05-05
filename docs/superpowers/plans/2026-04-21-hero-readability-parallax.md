# Hero Readability + Parallax Scroll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix hero text readability with a strong gradient scrim, replace the headline fade-in with a clip-mask curtain reveal, and add scroll-driven parallax depth to the hero section.

**Architecture:** All changes are isolated to `src/app/page.js`. The gradient layer gets a fixed high-contrast scrim. `EditorialHeadline` gets wrapper divs with `overflow: hidden` so lines animate as a curtain. Scroll parallax uses Framer Motion `useScroll`/`useTransform` on wrapper `motion.div`s that sit outside the existing `photoRef`/`textRef` divs — this avoids conflicts with the existing mouse-move handler.

**Tech Stack:** Next.js 14 App Router, Framer Motion 12 (`useScroll`, `useTransform`), React inline styles with CSS variables.

---

### Task 1: Strengthen the gradient scrim

**Files:**
- Modify: `src/app/page.js`

The current Layer 2 readability gradient has 22% max opacity — far too weak. Replace it with a fixed high-contrast scrim. Also remove the now-unused `bgColor` variable.

- [ ] **Step 1: Remove the `bgColor` variable**

In `src/app/page.js`, find and delete this line (around line 130):

```js
const bgColor = isDark ? '18,17,16' : '251,248,240';
```

- [ ] **Step 2: Replace the readability gradient**

Find Layer 2 (the div with comment `{/* Layer 2: Readability gradient mask */}`). Replace the entire div:

**Before:**
```jsx
{/* Layer 2: Readability gradient mask */}
<div
  aria-hidden="true"
  style={{
    position: 'absolute',
    inset: 0,
    background: `linear-gradient(90deg, rgba(${bgColor},0.22) 0%, rgba(${bgColor},0.08) 50%, transparent 100%)`,
    pointerEvents: 'none',
    zIndex: 1,
  }}
/>
```

**After:**
```jsx
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

- [ ] **Step 3: Verify build passes**

```bash
npm run build
```

Expected: no errors, no warnings about `bgColor`.

- [ ] **Step 4: Visual check**

```bash
npm run dev
```

Open `http://localhost:3000`. The hero headline should now be clearly readable against the photo. The right side of the photo should still be fully visible.

- [ ] **Step 5: Commit**

```bash
git add src/app/page.js
git commit -m "fix(hero): replace weak readability gradient with strong scrim"
```

---

### Task 2: Clip-mask curtain reveal on EditorialHeadline

**Files:**
- Modify: `src/app/page.js`

Replace the current `EditorialHeadline` per-line animation (opacity 0→1, y 20→0) with a curtain reveal. Each line gets an `overflow: hidden` wrapper div; the `motion.div` inside animates from `y: '110%'` to `y: '0%'`.

- [ ] **Step 1: Replace the `EditorialHeadline` component**

Find the `EditorialHeadline` function (around line 88). Replace the entire function:

**Before:**
```jsx
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
```

**After:**
```jsx
function EditorialHeadline({ line1, line2, line3, size = 'var(--text-3xl)' }) {
  const lines = [
    { text: line1, outline: false },
    { text: line2, outline: false },
    { text: line3, outline: true },
  ];
  return (
    <div style={{ marginBottom: 'var(--space-8)' }}>
      {lines.map(({ text, outline }, i) => (
        <div key={i} style={{ overflow: 'hidden', lineHeight: 1.05 }}>
          <motion.div
            initial={{ y: '110%' }}
            animate={{ y: '0%' }}
            transition={{ duration: 0.75, delay: 0.4 + i * 0.15, ease: [0.22, 1, 0.36, 1] }}
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
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Verify build passes**

```bash
npm run build
```

Expected: clean build, no errors.

- [ ] **Step 3: Visual check**

```bash
npm run dev
```

Open `http://localhost:3000`. Hard-refresh (Ctrl+Shift+R). The three headline lines should slide up one by one from behind an invisible mask — not fade in. Each line should be invisible until it slides into view. Timing: line 1 at 0.4s, line 2 at 0.55s, line 3 at 0.70s.

- [ ] **Step 4: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): replace headline fade-in with clip-mask curtain reveal"
```

---

### Task 3: Scroll-driven parallax depth

**Files:**
- Modify: `src/app/page.js`

Add `useScroll` and `useTransform` to the Framer Motion import. Wrap the photo layer and the text layer each in a `motion.div` that handles scroll-based `y` and `opacity`. The existing `photoRef`/`textRef` divs (used by mouse-move) remain as inner elements — this prevents transform conflicts.

- [ ] **Step 1: Update the Framer Motion import**

Find line 4:

```js
import { motion } from 'framer-motion';
```

Replace with:

```js
import { motion, useScroll, useTransform } from 'framer-motion';
```

- [ ] **Step 2: Add scroll transform values to the `Page` component**

Inside the `Page` function, after the existing `const isDark = theme === 'dark';` line, add:

```js
const { scrollY } = useScroll();
const heroHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
const photoScrollY = useTransform(scrollY, [0, heroHeight], ['0%', '20%']);
const textScrollY  = useTransform(scrollY, [0, heroHeight], ['0%', '-7%']);
const heroOpacity  = useTransform(scrollY, [0, heroHeight * 0.6], [1, 0]);
```

- [ ] **Step 3: Wrap the photo layer in a scroll `motion.div`**

Find `{/* Layer 0: Photo */}`. The current structure is a single `div` with `ref={photoRef}`. Wrap it in an outer `motion.div` that carries the scroll transforms, and move the `zIndex`/positioning to the wrapper:

**Before:**
```jsx
{/* Layer 0: Photo */}
<div
  ref={photoRef}
  style={{
    position: 'absolute',
    inset: '-10% -5%',
    backgroundImage: "url('/herofoto.jpeg')",
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    filter: `brightness(${isDark ? '0.65' : '0.80'}) saturate(0.75)`,
    willChange: 'transform',
    transition: 'transform 0.1s linear',
  }}
/>
```

**After:**
```jsx
{/* Layer 0: Photo */}
<motion.div style={{ position: 'absolute', inset: 0, y: photoScrollY, opacity: heroOpacity }}>
  <div
    ref={photoRef}
    style={{
      position: 'absolute',
      inset: '-10% -5%',
      backgroundImage: "url('/herofoto.jpeg')",
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      filter: `brightness(${isDark ? '0.65' : '0.80'}) saturate(0.75)`,
      willChange: 'transform',
      transition: 'transform 0.1s linear',
    }}
  />
</motion.div>
```

- [ ] **Step 4: Wrap the text content layer in a scroll `motion.div`**

Find `{/* Layer 3: Text content */}`. The current structure is a `div` with `ref={textRef}`. Wrap it similarly:

**Before:**
```jsx
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
```

**After:**
```jsx
{/* Layer 3: Text content */}
<motion.div style={{ position: 'relative', zIndex: 10, y: textScrollY, opacity: heroOpacity }}>
  <div
    ref={textRef}
    className="container"
    style={{
      paddingTop: 'var(--space-16)',
      paddingBottom: 'var(--space-16)',
      willChange: 'transform',
      transition: 'transform 0.1s linear',
    }}
  >
```

Close the new wrapper `</motion.div>` immediately after the closing `</div>` of the text content block (before the scroll indicator comment).

- [ ] **Step 5: Verify build passes**

```bash
npm run build
```

Expected: clean build, no TypeScript/JSX errors.

- [ ] **Step 6: Visual check — parallax**

```bash
npm run dev
```

Open `http://localhost:3000`. Scroll slowly past the hero section. Verify:
- The photo moves upward faster than the text (depth effect visible).
- The text moves upward more slowly.
- Both fade out smoothly as you approach the capabilities section.
- Moving your mouse over the hero still triggers the tilt effect (mouse-move parallax still works).

- [ ] **Step 7: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): add scroll-driven parallax depth and fade-out"
```
