'use client';

import { useScroll, useTransform, motion } from 'framer-motion';

export default function ParallaxBackground({ speed = 0.3, children }) {
  const { scrollY } = useScroll();
  const parallaxY = useTransform(scrollY, [0, 1000], [0, -speed * 300]);

  return (
    <motion.div style={{ y: parallaxY }}>
      {children}
    </motion.div>
  );
}
