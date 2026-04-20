'use client';

import { useEffect, useRef } from 'react';

export default function BlueprintRaster() {
  const ref = useRef(null);

  useEffect(() => {
    function onScroll() {
      if (ref.current) {
        ref.current.style.transform = `translateY(${window.scrollY * 0.15}px)`;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1,
        pointerEvents: 'none',
        backgroundImage: `
          linear-gradient(rgba(232,185,49,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(232,185,49,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
      }}
    />
  );
}
