'use client';

import { motion } from 'framer-motion';

const directionMap = {
  up:    { y: 30 },
  down:  { y: -30 },
  left:  { x: -30 },
  right: { x: 30 },
};

export default function AnimateIn({ children, delay = 0, direction = 'up' }) {
  return (
    <motion.div
      initial={{ opacity: 0, ...directionMap[direction] }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut', delay }}
      viewport={{ once: true, margin: '-50px' }}
    >
      {children}
    </motion.div>
  );
}
