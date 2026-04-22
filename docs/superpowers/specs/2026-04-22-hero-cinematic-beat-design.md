# Hero Scroll — Cinematic Beat Design

**Date:** 2026-04-22  
**File:** `src/app/page.js`  
**Status:** Approved

---

## Problem

The current hero scroll animation starts both the text fade and the photo upward movement at `scroll = 0`. There is no separation between the two, so the photo rises while the text is still visible — the two motions compete instead of sequencing.

---

## Solution: Three-Phase "Cinematic Beat"

Three scroll phases, each with one clear visual purpose.

### Phase 1 — FADE `(scroll 0 → 18% of viewport height)`

- Text opacity: `1 → 0`
- Text Y: `0% → -5%` (drifts lightly upward as it fades)
- Photo: stationary
- Scrim: stays fully in place (photo still half-hidden)

### Phase 2 — HOLD `(scroll 18% → 45% of viewport height)`

- Nothing moves. Intentional visual silence.
- User sees only the dark scrim over the frozen photo — deliberate tension before the reveal.

### Phase 3 — REVEAL `(scroll 45% → 100% of viewport height)`

- Photo rises: parallax `0% → +22%`
- Scrim dissolves: `opacity 1 → 0`, completes by 75% scroll
- Result: raw photo takes over as it floats upward

---

## Implementation

### New `useTransform` values (in `Page()`)

```js
// Was: [0, heroHeight * 0.25] → [1, 0]
const textOpacity  = useTransform(scrollY, [0, heroHeight * 0.18], [1, 0]);

// Was: [0, heroHeight] → ['0%', '-7%']
const textScrollY  = useTransform(scrollY, [0, heroHeight * 0.22], ['0%', '-5%']);

// Was: [0, heroHeight] → ['0%', '20%']
const photoScrollY = useTransform(scrollY, [heroHeight * 0.45, heroHeight], ['0%', '22%']);

// New — scrim gets its own opacity, decoupled from text
const scrimOpacity = useTransform(scrollY, [heroHeight * 0.45, heroHeight * 0.75], [1, 0]);
```

### JSX change: decouple scrim from text

**Before** — one `motion.div` with `textOpacity` wrapping both scrim layers and text:

```jsx
<motion.div style={{ ..., opacity: textOpacity }}>
  {/* Layer 1: Gold tint wash */}
  {/* Layer 2: Readability gradient scrim */}
</motion.div>

<motion.div style={{ ..., opacity: textOpacity }}>
  {/* Text content */}
</motion.div>
```

**After** — scrim gets `scrimOpacity`, text keeps `textOpacity`:

```jsx
<motion.div style={{ ..., opacity: scrimOpacity }}>
  {/* Layer 1: Gold tint wash */}
  {/* Layer 2: Readability gradient scrim */}
</motion.div>

<motion.div style={{ ..., opacity: textOpacity }}>
  {/* Text content */}
</motion.div>
```

---

## Files Changed

| File | Change |
|---|---|
| `src/app/page.js` | 4 transform values + 1 JSX `opacity` prop |

No new components, no new files.

---

## Out of Scope

- No changes to the photo itself (brightness, saturation, blur)
- No changes to mouse-parallax behavior
- No changes to the border strip or scroll indicator
- No other sections affected
