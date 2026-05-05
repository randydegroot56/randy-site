'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from './ThemeProvider';

/**
 * Shared glass card — Style C: offset shadow + full perimeter glow + sweep on hover.
 *
 * Props:
 *   offset   {boolean}    Show offset shadow behind card. Default: true.
 *   featured {boolean}    Stronger gold border + permanent ambient glow. Default: false.
 *   reveal   {boolean}    Clip-path wipe-in when scrolled into view. Default: true.
 *   style    {object}     Applied to the outermost wrapper for layout overrides.
 *   children {ReactNode}
 */
export default function GlassCard({
  children,
  offset = true,
  featured = false,
  reveal = true,
  style = {},
}) {
  const [hovered, setHovered] = useState(false);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const cardBg = isDark ? 'rgba(18,17,16,0.78)' : 'rgba(251,248,240,0.82)';

  const baseBorder  = featured ? 'rgba(232,185,49,0.40)' : 'rgba(232,185,49,0.18)';
  const hoverBorder = featured ? 'rgba(232,185,49,0.65)' : 'rgba(232,185,49,0.55)';

  const baseBoxShadow = featured ? '0 0 30px rgba(232,185,49,0.08)' : 'none';
  const hoverBoxShadow = featured
    ? '-2px 0 16px rgba(232,185,49,0.28), 2px 0 16px rgba(232,185,49,0.28), 0 -2px 16px rgba(232,185,49,0.28), 0 2px 16px rgba(232,185,49,0.28), 0 0 40px rgba(232,185,49,0.14), inset 0 0 30px rgba(232,185,49,0.04)'
    : '-2px 0 16px rgba(232,185,49,0.18), 2px 0 16px rgba(232,185,49,0.18), 0 -2px 16px rgba(232,185,49,0.18), 0 2px 16px rgba(232,185,49,0.18), 0 0 40px rgba(232,185,49,0.10), inset 0 0 30px rgba(232,185,49,0.03)';

  const card = (
    <div style={{ position: 'relative', ...style }}>
      {/* Offset shadow — positioned behind the main card */}
      {offset && (
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: '8px -8px -8px 8px',
            border: `1px solid ${hovered ? 'rgba(232,185,49,0.20)' : 'rgba(232,185,49,0.08)'}`,
            pointerEvents: 'none',
            transition: 'border-color 0.3s ease',
          }}
        />
      )}

      {/* Main card surface */}
      <motion.div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        animate={{
          x: hovered ? -3 : 0,
          y: hovered ? -3 : 0,
          borderColor: hovered ? hoverBorder : baseBorder,
          boxShadow: hovered ? hoverBoxShadow : baseBoxShadow,
        }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        style={{
          position: 'relative',
          background: cardBg,
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderWidth: '1px',
          borderStyle: 'solid',
          borderRadius: 0,
          overflow: 'hidden',
        }}
      >
        {/* Diagonal sweep on hover — plays once per hover entry */}
        <AnimatePresence>
          {hovered && (
            <motion.div
              key="sweep"
              initial={{ x: '-150%' }}
              animate={{ x: '150%' }}
              exit={{ x: '150%' }}
              transition={{ duration: 0.6, ease: 'easeInOut' }}
              style={{
                position: 'absolute',
                inset: 0,
                background:
                  'linear-gradient(105deg, transparent 30%, rgba(232,185,49,0.06) 45%, rgba(232,185,49,0.10) 50%, rgba(232,185,49,0.06) 55%, transparent 70%)',
                pointerEvents: 'none',
                zIndex: 2,
              }}
            />
          )}
        </AnimatePresence>

        {/* Content — above sweep */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </div>
      </motion.div>
    </div>
  );

  if (!reveal) return card;

  return (
    <motion.div
      initial={{ clipPath: 'inset(0 100% 0 0)', opacity: 0 }}
      whileInView={{ clipPath: 'inset(0 0% 0 0)', opacity: 1 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
    >
      {card}
    </motion.div>
  );
}
