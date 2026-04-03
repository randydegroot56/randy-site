'use client';

import { useEffect, useRef } from 'react';

/* ── Types ─────────────────────────────────────────────────── */

interface Props {
  nodeColor?:  string;
  pulseColor?: string;
  bgColor?:    string;
}

interface NodeParticle {
  x:  number;
  y:  number;
  z:  number;
  vx: number;
  vy: number;
  vz: number;
  r:  number;
}

interface FlowParticle {
  ai:    number; // source node index
  bi:    number; // target node index
  t:     number; // progress 0 → 1
  speed: number;
}

/* ── Constants ─────────────────────────────────────────────── */

const DEPTH      = 1400;   // deeper scene for more parallax
const FOCAL      = 500;
const MAX_DIST   = 260;    // more connections visible
const FLOW_EVERY = 280;    // more frequent pulse attempts
const SPEED      = 0.28;   // slower drift = more stable network
const TILT_Y     = 0.0018; // Y-yaw: ~1.7 full circles over 5800px scroll
const TILT_X     = 0.00010;// X-tilt: very gentle nod
const MAX_FLOWS  = 24;     // more concurrent pulses

/* ── Component ─────────────────────────────────────────────── */

export default function NetworkBackground({
  nodeColor  = '#E8B931',
  pulseColor = '#E8B931',
  bgColor    = 'transparent',
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let lastFlow = 0;

    /* ── Resize ── */
    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    /* ── Mouse state ── */
    let mouseNX = 0, mouseNY = 0;
    let smoothMX = 0, smoothMY = 0;
    const onMouseMove = (e: MouseEvent) => {
      mouseNX = (e.clientX / window.innerWidth  - 0.5) * 2;
      mouseNY = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', onMouseMove);

    /* ── Spawn nodes ── */
    const count = Math.min(
      Math.round((canvas.width * canvas.height) / 10_000),
      140,
    );

    const nodes: NodeParticle[] = Array.from({ length: count }, () => ({
      x:  (Math.random() - 0.5) * canvas.width,
      y:  (Math.random() - 0.5) * canvas.height,
      z:  Math.random() * DEPTH - DEPTH / 2,
      vx: (Math.random() - 0.5) * SPEED * 2,
      vy: (Math.random() - 0.5) * SPEED * 2,
      vz: (Math.random() - 0.5) * 0.35,
      r:  Math.random() * 1.4 + 0.8,
    }));

    const flows: FlowParticle[] = [];

    /* nodeIndex → remaining glow frames */
    const glows = new Map<number, number>();

    /* ── Projection (dual-axis: Y-yaw then X-tilt) ── */
    type Projected = { sx: number; sy: number; scale: number; rz: number } | null;

    const project = (
      wx: number, wy: number, wz: number,
      cosX: number, sinX: number,
      cosY: number, sinY: number,
      cx: number, cy: number,
    ): Projected => {
      // Y-axis rotation
      const rx  =  wx * cosY + wz * sinY;
      const rz0 = -wx * sinY + wz * cosY;
      // X-axis rotation
      const ry  = wy * cosX - rz0 * sinX;
      const rz  = wy * sinX + rz0 * cosX;
      // Perspective division
      const camZ = rz + FOCAL;
      if (camZ <= 0) return null;
      const scale = FOCAL / camZ;
      return { sx: cx + rx * scale, sy: cy + ry * scale, scale, rz };
    };

    /* ── Flow spawn (requires current projection) ── */
    const spawnFlow = (
      cosX: number, sinX: number,
      cosY: number, sinY: number,
      cx: number, cy: number,
    ) => {
      if (flows.length >= MAX_FLOWS) return;
      for (let attempt = 0; attempt < 30; attempt++) {
        const ai = Math.floor(Math.random() * nodes.length);
        const bi = Math.floor(Math.random() * nodes.length);
        if (ai === bi) continue;
        const pa = project(nodes[ai].x, nodes[ai].y, nodes[ai].z, cosX, sinX, cosY, sinY, cx, cy);
        const pb = project(nodes[bi].x, nodes[bi].y, nodes[bi].z, cosX, sinX, cosY, sinY, cx, cy);
        if (!pa || !pb) continue;
        const dx   = pa.sx - pb.sx;
        const dy   = pa.sy - pb.sy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MAX_DIST * Math.min(pa.scale, pb.scale)) {
          flows.push({ ai, bi, t: 0, speed: 0.007 + Math.random() * 0.006 });
          break;
        }
      }
    };

    /* ── Main tick ── */
    const tick = (ts: number) => {
      const w  = canvas.width;
      const h  = canvas.height;
      const cx = w / 2;
      const cy = h / 2;

      ctx.clearRect(0, 0, w, h);

      if (bgColor !== 'transparent') {
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, w, h);
      }

      /* Smooth mouse */
      smoothMX += (mouseNX - smoothMX) * 0.04;
      smoothMY += (mouseNY - smoothMY) * 0.04;

      /* Camera angles: Y-yaw is dominant (going around the network); X is gentle tilt */
      const scrollY = window.scrollY;
      const rotY = scrollY * TILT_Y  + smoothMX * 0.14;
      const rotX = scrollY * TILT_X  + smoothMY * 0.07;

      const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
      const cosY = Math.cos(rotY), sinY = Math.sin(rotY);

      /* Spawn flows on interval — two attempts per tick for density */
      if (ts - lastFlow > FLOW_EVERY) {
        spawnFlow(cosX, sinX, cosY, sinY, cx, cy);
        spawnFlow(cosX, sinX, cosY, sinY, cx, cy);
        lastFlow = ts;
      }

      /* Move nodes */
      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.z += n.vz;
        if (n.x < -w / 2 || n.x > w / 2) { n.vx *= -1; n.x = Math.max(-w / 2, Math.min(w / 2, n.x)); }
        if (n.y < -h / 2 || n.y > h / 2) { n.vy *= -1; n.y = Math.max(-h / 2, Math.min(h / 2, n.y)); }
        if (n.z >  DEPTH / 2) n.z -= DEPTH;
        if (n.z < -DEPTH / 2) n.z += DEPTH;
      }

      /* Project all nodes */
      const projected: Projected[] = nodes.map(n =>
        project(n.x, n.y, n.z, cosX, sinX, cosY, sinY, cx, cy),
      );

      /* Sort far-to-near */
      const order = Array.from({ length: nodes.length }, (_, i) => i)
        .filter(i => projected[i] !== null)
        .sort((a, b) => projected[b]!.rz - projected[a]!.rz);

      /* ── 1. Flow particles (comet along visible lines) ── */
      for (let i = flows.length - 1; i >= 0; i--) {
        const f = flows[i];
        f.t += f.speed;

        if (f.t >= 1) {
          /* Trigger arrival glow on target node */
          glows.set(f.bi, 25);
          flows.splice(i, 1);
          continue;
        }

        const a  = nodes[f.ai];
        const b  = nodes[f.bi];
        const pa = projected[f.ai];
        const pb = projected[f.bi];
        if (!pa || !pb) continue;

        /* Only render if the connection line is currently visible */
        const ldx  = pa.sx - pb.sx;
        const ldy  = pa.sy - pb.sy;
        const ldist = Math.sqrt(ldx * ldx + ldy * ldy);
        if (ldist >= MAX_DIST * Math.min(pa.scale, pb.scale)) continue;

        const alpha = Math.sin(f.t * Math.PI) * 0.75;

        /* Head position — interpolate live node world coords */
        const hx = a.x + (b.x - a.x) * f.t;
        const hy = a.y + (b.y - a.y) * f.t;
        const hz = a.z + (b.z - a.z) * f.t;

        /* Tail position (22% behind — longer comet) */
        const t0 = Math.max(0, f.t - 0.22);
        const tx = a.x + (b.x - a.x) * t0;
        const ty = a.y + (b.y - a.y) * t0;
        const tz = a.z + (b.z - a.z) * t0;

        const head = project(hx, hy, hz, cosX, sinX, cosY, sinY, cx, cy);
        const tail = project(tx, ty, tz, cosX, sinX, cosY, sinY, cx, cy);
        if (!head || !tail) continue;

        /* Gradient comet tail */
        const grad = ctx.createLinearGradient(tail.sx, tail.sy, head.sx, head.sy);
        grad.addColorStop(0, 'rgba(232,185,49,0)');
        grad.addColorStop(1, pulseColor);
        ctx.beginPath();
        ctx.moveTo(tail.sx, tail.sy);
        ctx.lineTo(head.sx, head.sy);
        ctx.strokeStyle = grad;
        ctx.lineWidth   = 2.0 * head.scale;
        ctx.globalAlpha = alpha;
        ctx.stroke();

        /* Bright head dot */
        ctx.beginPath();
        ctx.arc(head.sx, head.sy, 2.5 * head.scale, 0, Math.PI * 2);
        ctx.fillStyle   = pulseColor;
        ctx.globalAlpha = Math.min(alpha * 1.2, 0.85);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      /* ── 3. Connection lines ── */
      for (let ii = 0; ii < order.length; ii++) {
        const i  = order[ii];
        const pa = projected[i]!;

        for (let jj = ii + 1; jj < order.length; jj++) {
          const j  = order[jj];
          const pb = projected[j]!;

          const dx   = pa.sx - pb.sx;
          const dy   = pa.sy - pb.sy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const maxD = MAX_DIST * Math.min(pa.scale, pb.scale);
          if (dist >= maxD) continue;

          ctx.beginPath();
          ctx.moveTo(pa.sx, pa.sy);
          ctx.lineTo(pb.sx, pb.sy);
          ctx.strokeStyle = nodeColor;
          ctx.lineWidth   = 0.5;
          ctx.globalAlpha = Math.min(pa.scale, pb.scale) * (1 - dist / maxD) * 0.75;
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;

      /* ── 4. Nodes (glow halo + dot) ── */
      for (const i of order) {
        const n = nodes[i];
        const p = projected[i]!;

        /* Arrival glow halo */
        const g = glows.get(i) ?? 0;
        if (g > 0) {
          const glowT = g / 25;
          ctx.beginPath();
          ctx.arc(p.sx, p.sy, n.r * p.scale * (1 + glowT * 3), 0, Math.PI * 2);
          ctx.fillStyle   = pulseColor;
          ctx.globalAlpha = glowT * 0.35 * Math.min(p.scale * 1.5, 1);
          ctx.fill();
          glows.set(i, g - 1);
        }

        /* Outer soft glow halo */
        const outerR = n.r * p.scale * 8;
        const outerGrad = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, outerR);
        outerGrad.addColorStop(0,   `rgba(232,185,49,${Math.min(p.scale * 0.32, 0.32).toFixed(3)})`);
        outerGrad.addColorStop(0.3, `rgba(232,185,49,${Math.min(p.scale * 0.12, 0.12).toFixed(3)})`);
        outerGrad.addColorStop(1,   'rgba(232,185,49,0)');
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, outerR, 0, Math.PI * 2);
        ctx.fillStyle   = outerGrad;
        ctx.globalAlpha = 1;
        ctx.fill();

        /* Inner bright core — fades to transparent at edge */
        const coreR = n.r * p.scale * 2.2;
        const coreGrad = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, coreR);
        coreGrad.addColorStop(0,    nodeColor);
        coreGrad.addColorStop(0.35, nodeColor);
        coreGrad.addColorStop(1,    'rgba(232,185,49,0)');
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, coreR, 0, Math.PI * 2);
        ctx.fillStyle   = coreGrad;
        ctx.globalAlpha = Math.min(p.scale * 1.4, 0.95);
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMouseMove);
    };
  }, [nodeColor, pulseColor, bgColor]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position:      'fixed',
        inset:         0,
        zIndex:        0,
        pointerEvents: 'none',
        display:       'block',
      }}
    />
  );
}
