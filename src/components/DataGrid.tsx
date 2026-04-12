'use client';

import { useScroll, useTransform, motion } from 'framer-motion';

export default function DataGrid() {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 3000], [0, -150]);

  return (
    <motion.div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1,
        pointerEvents: 'none',
        y,
        backgroundImage: `
          linear-gradient(rgba(232,185,49,0.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(232,185,49,0.025) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
      }}
    >
      {/* Corner coordinate labels */}
      <span style={{
        position: 'absolute',
        top: 12,
        left: 16,
        fontFamily: 'monospace',
        fontSize: '10px',
        color: 'rgba(232,185,49,0.15)',
        letterSpacing: '0.05em',
        userSelect: 'none',
      }}>
        51.9225°N / 4.4792°E
      </span>
      <span style={{
        position: 'absolute',
        top: 12,
        right: 16,
        fontFamily: 'monospace',
        fontSize: '10px',
        color: 'rgba(232,185,49,0.15)',
        letterSpacing: '0.05em',
        userSelect: 'none',
      }}>
        NL.RE.GRID_v1
      </span>
      <span style={{
        position: 'absolute',
        bottom: 12,
        left: 16,
        fontFamily: 'monospace',
        fontSize: '10px',
        color: 'rgba(232,185,49,0.1)',
        letterSpacing: '0.05em',
        userSelect: 'none',
      }}>
        AMS / RTD / UTR
      </span>
    </motion.div>
  );
}
