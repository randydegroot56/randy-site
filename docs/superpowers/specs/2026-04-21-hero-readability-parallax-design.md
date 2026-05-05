# Hero Readability + Parallax Scroll — Design Spec

**Date:** 2026-04-21  
**File affected:** `src/app/page.js`  
**Status:** Approved

---

## Problem

The hero text on randy.dev is hard to read. Three root causes:

1. The readability gradient mask has only 22% max opacity — insufficient contrast against the photo.
2. `EditorialHeadline` lines have no `textShadow`; the outline variant (line 3) is especially hard to read on a busy photo background.
3. No scroll-based depth — the hero feels flat on scroll.

---

## Solution Overview

Three targeted changes to `src/app/page.js`:

1. **Gradient Scrim** — replace the weak readability layer with a strong left-to-right gradient.
2. **Clip-Mask Curtain Reveal** — replace the current `EditorialHeadline` fade-in with a per-line curtain animation.
3. **Parallax Scroll** — add scroll-driven depth: text moves slower than the photo, both fade out.

---

## 1. Gradient Scrim

**Replace** Layer 2 (the current readability gradient) with:

```css
linear-gradient(
  90deg,
  rgba(12,10,8,0.88) 0%,
  rgba(12,10,8,0.72) 30%,
  rgba(12,10,8,0.22) 65%,
  transparent 100%
)
```

- Left ~30%: ~85% dark — text always readable regardless of photo content.
- Fades to transparent on the right — photo remains fully visible on the right half.
- Works in both light and dark theme (the scrim color is a fixed near-black, matching the darkened photo).
- Remove the `bgColor` variable logic that was driving the old gradient — it's no longer needed for this layer.

---

## 2. Clip-Mask Curtain Reveal

**Replace** the `EditorialHeadline` component's current animation (opacity 0→1, y 20→0) with a curtain reveal per line.

Each line is wrapped in an `overflow: hidden` container div. The `motion.div` inside animates from `y: '110%'` to `y: '0%'`, creating the effect of text sliding up from behind a mask.

```jsx
// Wrapper — clips the overflow
<div style={{ overflow: 'hidden', lineHeight: '1.05' }}>
  <motion.div
    initial={{ y: '110%' }}
    animate={{ y: '0%' }}
    transition={{
      duration: 0.75,
      delay: 0.4 + i * 0.15,
      ease: [0.22, 1, 0.36, 1],
    }}
    style={{ /* existing text styles */ }}
  >
    {text}
  </motion.div>
</div>
```

Timing:
- Line 1: delay 0.40s
- Line 2: delay 0.55s
- Line 3: delay 0.70s

The `EditorialHeadline` wrapper `<div>` keeps `marginBottom: 'var(--space-8)'` and no outer animation — only the per-line curtain animates.

---

## 3. Parallax Scroll

Add `useScroll` and `useTransform` from Framer Motion to `page.js`.

### Scroll targets

```jsx
const { scrollY } = useScroll();
const heroHeight = typeof window !== 'undefined' ? window.innerHeight : 800;

// Photo moves up faster (further away = moves more)
const photoScrollY = useTransform(scrollY, [0, heroHeight], ['0%', '20%']);

// Text moves up slower (closer to viewer = moves less)
const textScrollY = useTransform(scrollY, [0, heroHeight], ['0%', '-7%']);

// Both fade out by 60% scroll through the hero
const heroOpacity = useTransform(scrollY, [0, heroHeight * 0.6], [1, 0]);
```

### Application

- `photoRef` div: add `y: photoScrollY` and `opacity: heroOpacity` via `motion.div` (convert from plain `div` to `motion.div`).
- `textRef` div: add `y: textScrollY` and `opacity: heroOpacity` via `motion.div` (already wrapped with ref, convert to `motion.div`).

The existing mouse-move parallax (`handleHeroMouseMove` / `handleHeroMouseLeave`) uses inline `style.transform` directly on the DOM refs — this continues to work alongside Framer Motion's scroll transforms because Framer Motion applies its own transform values separately via the `style` prop.

### SSR safety

`window.innerHeight` is only available in the browser. Guard with:
```js
const heroHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
```

---

## Constraints

- No new dependencies — `useScroll` and `useTransform` are already available in Framer Motion 12.
- All styles remain inline React style objects referencing CSS variables.
- The mouse-move parallax (`photoRef`, `textRef`) is preserved as-is.
- The scroll indicator at the bottom of the hero is unaffected.
- No changes to other sections (capabilities, projects, about, CTA).

---

## Files Changed

| File | Change |
|------|--------|
| `src/app/page.js` | Scrim gradient, EditorialHeadline curtain reveal, scroll parallax |

No new files. No other files touched.
