'use client';

import { useScroll, useTransform, motion } from 'framer-motion';

const DRAW_DURATION = 2.5;

// Note: SVG stroke/fill attributes use hardcoded rgba() values.
// CSS custom properties (var(--accent-primary)) work for CSS style properties
// but not reliably for SVG presentation attributes with per-element opacity variants.
// Values match the design system: #E8B931 = --accent-primary.

// Each path group draws in at a different delay for a staggered reveal
function pathAnim(delay: number) {
  return {
    hidden: { pathLength: 0, opacity: 0 },
    visible: {
      pathLength: 1,
      opacity: 1,
      transition: { pathLength: { duration: DRAW_DURATION, delay, ease: 'easeInOut' }, opacity: { duration: 0.3, delay } },
    },
  } as const;
}

export default function CityskylineBackground() {
  const { scrollY } = useScroll();
  // Skyline moves up at 0.15× scroll speed
  const y = useTransform(scrollY, [0, 3000], [0, -450]);

  return (
    <motion.div
      aria-hidden="true"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 2,
        pointerEvents: 'none',
        y,
        opacity: 0.32,
      }}
    >
      <svg
        viewBox="0 0 1440 300"
        preserveAspectRatio="xMidYMax meet"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', display: 'block' }}
      >
        {/* ── Ground line ──────────────────────────────── */}
        <motion.line
          x1="0" y1="292" x2="1440" y2="292"
          stroke="rgba(232,185,49,0.5)"
          strokeWidth="1"
          variants={pathAnim(0)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Left buildings cluster ───────────────────── */}
        <motion.path
          d="M 0,292 L 0,240 L 38,240 L 38,225 L 55,225 L 55,210 L 68,210 L 68,198 L 83,198 L 83,185 L 98,185 L 98,172 L 112,172 L 112,158 L 128,158 L 128,144 L 148,144 L 148,130 L 168,130 L 168,118 L 190,118 L 190,130 L 208,130 L 208,118 L 228,118 L 228,130 L 242,130 L 242,118 L 258,118 L 258,132 L 272,132 L 272,145 L 290,145 L 290,158 L 308,158 L 308,170 L 326,170 L 326,182 L 345,182 L 345,195 L 365,195 L 365,210 L 380,210"
          fill="none"
          stroke="rgba(232,185,49,0.75)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(0.1)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Bridge approach ramps ─────────────────────── */}
        <motion.path
          d="M 378,228 L 665,228"
          fill="none"
          stroke="rgba(232,185,49,0.8)"
          strokeWidth="2"
          variants={pathAnim(0.35)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Erasmus Bridge pylon (main shaft, leans left) */}
        <motion.path
          d="M 464,228 L 448,38"
          fill="none"
          stroke="#E8B931"
          strokeWidth="2.5"
          strokeLinecap="round"
          variants={pathAnim(0.5)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Pylon A-frame right support leg ──────────── */}
        <motion.path
          d="M 448,38 L 470,148"
          fill="none"
          stroke="rgba(232,185,49,0.9)"
          strokeWidth="2"
          strokeLinecap="round"
          variants={pathAnim(0.7)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Bridge cables — left side (5 cables) ─────── */}
        <motion.path
          d="M 448,38 L 382,226 M 448,38 L 402,226 M 448,38 L 420,226 M 448,38 L 438,226 M 448,38 L 455,226"
          fill="none"
          stroke="rgba(232,185,49,0.5)"
          strokeWidth="1"
          variants={pathAnim(0.85)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Bridge cables — right side (10 cables) ───── */}
        <motion.path
          d="M 448,38 L 478,226 M 448,38 L 500,226 M 448,38 L 522,226 M 448,38 L 544,226 M 448,38 L 565,226 M 448,38 L 586,226 M 448,38 L 607,226 M 448,38 L 628,226 M 448,38 L 648,226 M 448,38 L 663,226"
          fill="none"
          stroke="rgba(232,185,49,0.45)"
          strokeWidth="1"
          variants={pathAnim(0.95)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Centre buildings (between bridge & Euromast) */}
        <motion.path
          d="M 665,228 L 665,195 L 690,195 L 690,180 L 712,180 L 712,165 L 732,165 L 732,155 L 752,155 L 752,162 L 772,162 L 772,172 L 792,172 L 792,182 L 810,182"
          fill="none"
          stroke="rgba(232,185,49,0.7)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(1.25)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Euromast shaft ────────────────────────────── */}
        <motion.path
          d="M 822,292 L 822,15"
          fill="none"
          stroke="rgba(232,185,49,0.9)"
          strokeWidth="1.8"
          strokeLinecap="round"
          variants={pathAnim(1.45)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Euromast observation disc ─────────────────── */}
        <motion.path
          d="M 806,105 L 838,105 L 838,122 L 806,122 Z M 814,105 L 814,95 L 830,95 L 830,105"
          fill="none"
          stroke="rgba(232,185,49,0.85)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(1.6)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Euromast tip dot ──────────────────────────── */}
        <motion.circle
          cx="822" cy="15" r="3"
          fill="#E8B931"
          variants={{
            hidden: { opacity: 0, scale: 0 },
            visible: { opacity: 1, scale: 1, transition: { duration: 0.4, delay: 1.8 } },
          }}
          initial="hidden"
          animate="visible"
        />

        {/* ── Right buildings cluster ───────────────────── */}
        <motion.path
          d="M 838,292 L 838,192 L 862,192 L 862,175 L 885,175 L 885,160 L 908,160 L 908,148 L 932,148 L 932,158 L 952,158 L 952,170 L 972,170 L 972,182 L 995,182 L 995,195 L 1020,195 L 1020,208 L 1050,208 L 1050,220 L 1085,220 L 1085,230 L 1125,230 L 1125,240 L 1170,240 L 1170,248 L 1222,248 L 1222,256 L 1285,256 L 1285,264 L 1355,264 L 1355,272 L 1440,272 L 1440,292"
          fill="none"
          stroke="rgba(232,185,49,0.65)"
          strokeWidth="1.5"
          strokeLinejoin="round"
          variants={pathAnim(1.75)}
          initial="hidden"
          animate="visible"
        />

        {/* ── Stars ─────────────────────────────────────── */}
        <motion.g
          variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { duration: 1, delay: 2.2 } } }}
          initial="hidden"
          animate="visible"
        >
          {/* 4-point star (like in reference image) */}
          <path d="M 280,45 L 284,52 L 291,55 L 284,58 L 280,65 L 276,58 L 269,55 L 276,52 Z"
            fill="rgba(232,185,49,0.6)" />
          {/* Moon crescent */}
          <path d="M 1180,35 Q 1200,40 1200,58 Q 1200,76 1180,80 Q 1196,72 1196,58 Q 1196,44 1180,35 Z"
            fill="rgba(232,185,49,0.55)" />
          {/* Small dot stars */}
          <circle cx="120" cy="30" r="1.5" fill="rgba(232,185,49,0.4)" />
          <circle cx="600" cy="22" r="1.2" fill="rgba(232,185,49,0.35)" />
          <circle cx="950" cy="40" r="1.5" fill="rgba(232,185,49,0.3)" />
          <circle cx="1320" cy="28" r="1.2" fill="rgba(232,185,49,0.4)" />
        </motion.g>
      </svg>
    </motion.div>
  );
}
