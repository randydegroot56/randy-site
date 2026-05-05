# Hero Sticky Cinematic Scroll — Design Spec

**Date:** 2026-04-22  
**Status:** Approved

---

## Goal

Replace the current `scrollY`-pixel-based hero scroll animation with a sticky cinematic scroll sequence. The hero visually locks in place while the user scrolls through ~200vh of dedicated scroll space. The animation unfolds in three acts: text + scrim dissolve together, a full-photo "moment", then the photo dramatically surges upward and disappears.

---

## Architecture

### Wrapper structure

```
<div ref={wrapperRef} style={{ height: '200vh', scrollSnapAlign: 'start' }}>
  <section style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden' }}>
    {/* photo, scrim, text, indicators */}
  </section>
</div>
<div style={{ height: '45vh' }} />   {/* existing spacer */}
{/* next snap-section */}
```

The 200vh wrapper gets `scroll-snap-align: start` so the page snaps to the beginning of the cinematic zone. The hero `<section>` no longer needs `scroll-snap-align` itself.

### Scroll progress

```js
const wrapperRef = useRef(null);
const { scrollYProgress } = useScroll({
  target: wrapperRef,
  offset: ['start start', 'end end'],
});
```

`scrollYProgress` runs 0→1 over the full 200vh. All animation transforms use this normalized value — no `window.innerHeight`, no pixel hacks.

---

## Animation Phases

| Phase | scrollYProgress | What happens |
|---|---|---|
| Act 1 | 0.00 → 0.20 | Scroll indicator fades out |
| Act 1 | 0.00 → 0.30 | Text drifts up slightly + fades out. Scrim fades out simultaneously. |
| Act 2 | 0.30 → 0.75 | Everything holds still. Full photo, no text, no scrim. Mouse parallax still active. |
| Act 3 | 0.75 → 1.00 | Photo shoots upward (y: 0% → -120%) and hard-fades (opacity: 1 → 0). |

---

## useTransform Definitions

```js
// Scroll indicator
const indicatorOpacity = useTransform(scrollYProgress, [0, 0.20], [1, 0]);

// Text
const textOpacity = useTransform(scrollYProgress, [0, 0.30], [1, 0]);
const textY       = useTransform(scrollYProgress, [0, 0.30], ['0%', '-4%']);

// Scrim (same timing as text)
const scrimOpacity = useTransform(scrollYProgress, [0, 0.30], [1, 0]);

// Photo
const photoY       = useTransform(scrollYProgress, [0.75, 1.0], ['0%', '-120%']);
const photoOpacity = useTransform(scrollYProgress, [0.75, 1.0], [1, 0]);
```

The photo no longer needs a `px`-based counteract transform. `position: sticky` on the hero section keeps the photo fixed in the viewport automatically.

---

## Mouse Parallax

The existing `handleHeroMouseMove` / `handleHeroMouseLeave` logic stays unchanged. During Act 2 ("the moment"), the photo is fully visible and the mouse parallax gives it life. No changes needed.

---

## What Is Removed

- `const { scrollY } = useScroll()` — replaced by `scrollYProgress` on the wrapper ref
- `const photoScrollY = useTransform(scrollY, [...], [...])` — the px-based sticky hack is fully removed
- `heroHeight` / `window.innerHeight` calculations — no longer needed
- `height: 'calc(100vh - 4rem)'` on the section — replaced by `height: '100vh'` (the sticky hero fills the viewport)

---

## Scroll Snap Behavior

The homepage uses `scroll-snap-type: y proximity`. The 200vh wrapper gets `scroll-snap-align: start`. When the user first lands, the page snaps to the start of the hero. After scrolling through the full 200vh (completing all three acts), the next `snap-section` (capabilities) comes into range and the page snaps to it.

The `snap-section` CSS class on the capabilities section already provides `scroll-snap-align: center` — no changes needed there.

---

## Mobile Considerations

`position: sticky` is well-supported across modern browsers including iOS Safari. The `200vh` scroll space works on touch devices — the user scrolls normally, the hero sticks. No special mobile overrides needed. If the animation feels too slow on small screens, the phase percentages can be tightened in a follow-up.

---

## Files Changed

- `src/app/page.js` — all changes are contained here. No new files, no shared components modified.
