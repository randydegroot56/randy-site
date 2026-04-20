'use client';

export default function AuroraBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      <style>{`
        @keyframes aurora1 {
          0%, 100% { opacity: 0.06; transform: scale(1) translate(0, 0); }
          50%       { opacity: 0.12; transform: scale(1.1) translate(2%, 1%); }
        }
        @keyframes aurora2 {
          0%, 100% { opacity: 0.04; transform: scale(1) translate(0, 0); }
          50%       { opacity: 0.09; transform: scale(1.08) translate(-2%, -1%); }
        }
        @keyframes aurora3 {
          0%, 100% { opacity: 0.03; transform: scale(1); }
          50%       { opacity: 0.07; transform: scale(1.05); }
        }
        @media (prefers-reduced-motion: reduce) {
          .aurora-orb { animation: none !important; }
        }
      `}</style>

      <div className="aurora-orb" style={{ position: 'absolute', top: '-10%', left: '-5%', width: '55%', height: '60%', background: 'radial-gradient(ellipse, rgba(232,185,49,0.18) 0%, transparent 70%)', animation: 'aurora1 14s ease-in-out infinite' }} />
      <div className="aurora-orb" style={{ position: 'absolute', bottom: '-15%', right: '-5%', width: '50%', height: '55%', background: 'radial-gradient(ellipse, rgba(232,185,49,0.12) 0%, transparent 70%)', animation: 'aurora2 19s ease-in-out 7s infinite' }} />
      <div className="aurora-orb" style={{ position: 'absolute', top: '30%', left: '35%', width: '35%', height: '40%', background: 'radial-gradient(ellipse, rgba(232,185,49,0.08) 0%, transparent 70%)', animation: 'aurora3 24s ease-in-out 12s infinite' }} />
    </div>
  );
}
