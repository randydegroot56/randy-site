# Hero Cinematic Beat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current simultaneous hero scroll animation with a three-phase cinematic sequence: text fades fast → intentional hold → scrim dissolves and photo surges upward.

**Architecture:** Four `useTransform` value changes and one JSX `opacity` prop swap in `src/app/page.js`. The scrim and the text content, currently sharing the same `textOpacity` motion value, are decoupled so each can animate independently.

**Tech Stack:** Framer Motion `useTransform`, React, Next.js 14

---

## File Map

| File | Change |
|---|---|
| `src/app/page.js:133-136` | Replace 3 transforms, add 1 new `scrimOpacity` |
| `src/app/page.js:201` | Swap `opacity: textOpacity` → `opacity: scrimOpacity` on scrim wrapper |

---

### Task 1: Update scroll transform values

**Files:**
- Modify: `src/app/page.js:133-136`

- [ ] **Step 1: Open `src/app/page.js` and locate the transform block**

Find lines 133–136 (inside the `Page()` component, just after `const { scrollY } = useScroll()`):

```js
const photoScrollY = useTransform(scrollY, [0, heroHeight], ['0%', '20%']);
const textScrollY  = useTransform(scrollY, [0, heroHeight], ['0%', '-7%']);
const textOpacity  = useTransform(scrollY, [0, heroHeight * 0.25], [1, 0]);
```

- [ ] **Step 2: Replace those three lines and add `scrimOpacity`**

```js
const photoScrollY = useTransform(scrollY, [heroHeight * 0.45, heroHeight], ['0%', '22%']);
const textScrollY  = useTransform(scrollY, [0, heroHeight * 0.22], ['0%', '-5%']);
const textOpacity  = useTransform(scrollY, [0, heroHeight * 0.18], [1, 0]);
const scrimOpacity = useTransform(scrollY, [heroHeight * 0.45, heroHeight * 0.75], [1, 0]);
```

What this achieves:
- `textOpacity`: text gone by 18% scroll (was 25%)
- `textScrollY`: text drifts up only until 22% scroll (was full viewport height, -7%)
- `photoScrollY`: photo doesn't move at all until 45% scroll, then rises to +22%
- `scrimOpacity`: scrim stays solid until 45%, fully gone by 75% (independent of text)

---

### Task 2: Decouple scrim opacity from text opacity

**Files:**
- Modify: `src/app/page.js:201`

- [ ] **Step 1: Find the scrim wrapper `motion.div`**

Around line 201, locate:

```jsx
{/* Layers 1 + 2: Scrim (fades with text) */}
<motion.div style={{ position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none', opacity: textOpacity }}>
```

- [ ] **Step 2: Replace `opacity: textOpacity` with `opacity: scrimOpacity`**

```jsx
{/* Layers 1 + 2: Scrim (dissolves in phase 3) */}
<motion.div style={{ position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none', opacity: scrimOpacity }}>
```

The text content layer (around line 223) already has its own `motion.div` with `opacity: textOpacity` — leave that unchanged.

---

### Task 3: Verify in browser and commit

**Files:** none

- [ ] **Step 1: Start the dev server**

```bash
npm run dev
```

Open `http://localhost:3000`.

- [ ] **Step 2: Scroll slowly through the hero and verify all three phases**

| Phase | Scroll position | What you should see |
|---|---|---|
| FADE | 0–18% of viewport | Text fades and drifts up. Photo still. Scrim still dark. |
| HOLD | 18–45% of viewport | Screen frozen. Dark scrim, frozen photo, no text. |
| REVEAL | 45–100% of viewport | Scrim dissolves. Photo rises from bottom. |

- [ ] **Step 3: Run a production build to confirm no errors**

```bash
npm run build
```

Expected: `✓ Compiled successfully` with no errors or warnings about the changed transforms.

- [ ] **Step 4: Commit**

```bash
git add src/app/page.js
git commit -m "feat(hero): cinematic beat scroll — text fades fast, hold, then photo reveals"
```
