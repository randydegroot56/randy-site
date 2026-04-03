'use client';

import { useTheme } from './ThemeProvider';

export default function TechBackground() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const lineOpacity      = isDark ? 0.14 : 0.10;
  const dotOpacity       = isDark ? 0.20 : 0.14;
  const circleOpacity    = isDark ? 0.10 : 0.07;
  const connectorOpacity = isDark ? 0.12 : 0.07;

  const svg = [
    `<svg xmlns='http://www.w3.org/2000/svg' width='160' height='80'>`,

    // Tile-edge grid lines (seamless tiling)
    `<line x1='160' y1='0' x2='160' y2='80' stroke='rgba(232,185,49,${lineOpacity})' stroke-width='0.5'/>`,
    `<line x1='0' y1='80' x2='160' y2='80' stroke='rgba(232,185,49,${lineOpacity})' stroke-width='0.5'/>`,

    // Corner dot at grid intersection
    `<circle cx='160' cy='80' r='1.5' fill='rgba(232,185,49,${dotOpacity})'/>`,

    // Half-tile rhythm dots (subdued — break regularity without adding full lines)
    `<circle cx='80'  cy='80' r='1' fill='rgba(232,185,49,${dotOpacity * 0.6})'/>`,
    `<circle cx='160' cy='40' r='1' fill='rgba(232,185,49,${dotOpacity * 0.6})'/>`,

    // Solder-pad circles — placed at opposite quadrants for diagonal rhythm
    `<circle cx='40'  cy='20' r='7' fill='none' stroke='rgba(232,185,49,${circleOpacity})' stroke-width='0.5'/>`,
    `<circle cx='120' cy='60' r='7' fill='none' stroke='rgba(232,185,49,${circleOpacity})' stroke-width='0.5'/>`,

    // L-trace #1 — bottom-left: run right then down to edge
    `<polyline points='0,60 24,60 24,80'    fill='none' stroke='rgba(232,185,49,${connectorOpacity})' stroke-width='0.5'/>`,
    // L-trace #2 — top-right: run down then right to edge
    `<polyline points='120,0 120,20 160,20' fill='none' stroke='rgba(232,185,49,${connectorOpacity})' stroke-width='0.5'/>`,
    // Connector trace — jogs from solder-pad circle #1 area upward
    `<polyline points='40,40 80,40 80,20'   fill='none' stroke='rgba(232,185,49,${connectorOpacity})' stroke-width='0.5'/>`,

    // Terminal dots at open ends of traces (PCB solder pads)
    `<circle cx='0'   cy='60' r='1.2' fill='rgba(232,185,49,${dotOpacity})'/>`,
    `<circle cx='120' cy='0'  r='1.2' fill='rgba(232,185,49,${dotOpacity})'/>`,
    `<circle cx='80'  cy='20' r='1.2' fill='rgba(232,185,49,${dotOpacity})'/>`,

    `</svg>`,
  ].join('');

  const pattern  = `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
  const gradient = `radial-gradient(ellipse 70% 60% at 50% 30%, rgba(232,185,49,0.05) 0%, transparent 60%)`;

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        backgroundImage: `${gradient}, ${pattern}`,
        backgroundRepeat: 'no-repeat, repeat',
        backgroundSize: 'cover, 160px 80px',
      }}
    />
  );
}
