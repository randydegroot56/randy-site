/*
  ============================================
  THEME TOGGLE KNOP
  ============================================
  
  Een geanimeerde zon/maan knop.
  
  HOE DE ANIMATIE WERKT:
  
  We gebruiken SVG (Scalable Vector Graphics) voor de iconen.
  SVG is perfect voor iconen omdat:
  - Het schaalt zonder kwaliteitsverlies
  - Je individuele delen kunt animeren
  - Het is gewoon XML/HTML — geen image files nodig
  
  De "truc" is CSS transforms:
  - rotate() draait het element
  - scale() maakt het groter/kleiner
  - opacity verandert de zichtbaarheid
  
  Met transition worden deze veranderingen geanimeerd
  in plaats van instant.
  
  ============================================
*/

'use client';

import { useTheme } from './ThemeProvider';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      aria-label={`Schakel naar ${isDark ? 'light' : 'dark'} mode`}
      style={{
        /* Reset default button styling */
        background: 'none',
        border: `1px solid var(--border-default)`,
        borderRadius: 'var(--radius-full)',
        
        /* Sizing */
        width: '44px',
        height: '44px',
        
        /* Centering the icon */
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        
        /* Interactie */
        cursor: 'pointer',
        transition: `all var(--transition-base)`,
        color: 'var(--text-primary)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--accent-primary)';
        e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--border-default)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      {/* SVG icon — zon of maan */}
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          transition: `transform var(--transition-base)`,
          transform: isDark ? 'rotate(180deg)' : 'rotate(0deg)',
        }}
      >
        {isDark ? (
          /* Maan icoon */
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        ) : (
          /* Zon icoon — cirkel + stralen */
          <>
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </>
        )}
      </svg>
    </button>
  );
}
