# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev      # Start development server
npm run build    # Production build
npm run start    # Start production server
```

No lint or test scripts are configured.

## Architecture

**Randy.dev** is a Next.js 14 portfolio site (App Router, `src/app/`) using React 18 and Framer Motion. All content is hardcoded — no CMS, no API calls.

### Routing
- `src/app/page.js` — home (hero, design system showcase, projects preview)
- `src/app/about/page.js` — bio and tech stack
- `src/app/work/page.js` — detailed project cards
- `src/app/blog/page.js` — blog listing

### Theming
`ThemeProvider` (Context API) manages a `data-theme="light|dark"` attribute on `<html>`, persisted to localStorage with system preference fallback. All colors are CSS variables defined in `src/styles/globals.css` under `[data-theme="light"]` and `[data-theme="dark"]` selectors.

### Styling
No CSS framework or CSS Modules — styling is done with inline React style objects referencing CSS variables (e.g., `var(--color-bg-primary)`). The full design system (colors, type scale, spacing, shadows, border radius) lives in `src/styles/globals.css`. Fonts: Space Grotesk (headings) and Source Serif 4 (body), loaded via Google Fonts in `layout.js`.

### Animation
Framer Motion wrappers in `src/components/`:
- `AnimateIn` — scroll-triggered directional fade-in (`direction` prop: `up|down|left|right`)
- `StaggerChildren` — staggers child entrance animations for grids
- `PageTransition` — fade-in on page load

### Duplicate root files
There are duplicate files at the project root (`layout.js`, `page.js`, `globals.css`, `ThemeProvider.jsx`, `ThemeToggle.jsx`). The authoritative source files are in `src/`. The root copies can be ignored.
