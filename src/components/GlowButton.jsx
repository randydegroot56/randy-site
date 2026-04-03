'use client';

import { motion } from 'framer-motion';
import MagneticButton from './MagneticButton';

export default function GlowButton({ children, onClick, style = {} }) {
  return (
    <MagneticButton>
      <motion.button
        onClick={onClick}
        whileHover={{
          boxShadow: '0 0 20px rgba(232,185,49,0.4), 0 0 40px rgba(232,185,49,0.2)',
        }}
        whileTap={{ scale: 0.97 }}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-3) var(--space-8)',
          borderRadius: 'var(--radius-full)',
          backgroundColor: 'var(--accent-primary)',
          color: '#121110',
          fontFamily: 'var(--font-heading)',
          fontWeight: 600,
          fontSize: 'var(--text-base)',
          cursor: 'pointer',
          border: 'none',
          ...style,
        }}
      >
        {children}
      </motion.button>
    </MagneticButton>
  );
}
