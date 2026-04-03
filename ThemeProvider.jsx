/*
  ============================================
  THEME PROVIDER
  ============================================
  
  HOE DARK MODE WERKT:
  
  1. We zetten een "data-theme" attribuut op het <html> element
     → <html data-theme="dark"> of <html data-theme="light">
  
  2. Onze CSS variabelen luisteren naar dit attribuut:
     → [data-theme="dark"] { --bg-primary: #141210; }
     → [data-theme="light"] { --bg-primary: #FAF8F5; }
  
  3. Alle componenten gebruiken var(--bg-primary) etc.
     → Ze hoeven NIET te weten welk theme actief is!
  
  4. We slaan de keuze op in localStorage, zodat het
     onthouden wordt na een page refresh.
  
  WAT IS CONTEXT?
  
  React Context is een manier om data te delen met ALLE
  componenten in je app, zonder het door elke laag te passen.
  
  Normaal: App → Layout → Header → ThemeToggle (props doorsturen)
  Met Context: ThemeProvider wraps alles, elk component kan
  het theme direct opvragen met useTheme().
  
  ============================================
*/

'use client';  // Dit vertelt Next.js dat dit component in de browser draait

import { createContext, useContext, useEffect, useState } from 'react';

// 1. Maak een "Context" aan — een gedeelde data-container
const ThemeContext = createContext({
  theme: 'light',
  toggleTheme: () => {},
});

// 2. Custom hook — maakt het makkelijk om het theme te gebruiken
//    In elk component: const { theme, toggleTheme } = useTheme();
export function useTheme() {
  return useContext(ThemeContext);
}

// 3. De Provider component — wraps je hele app
export default function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  const [mounted, setMounted] = useState(false);

  // Bij eerste load: check of er een opgeslagen voorkeur is
  useEffect(() => {
    // Check localStorage (eerder opgeslagen keuze)
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Geen opgeslagen keuze? Check systeem-voorkeur
      // (Windows/Mac dark mode instelling)
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(prefersDark ? 'dark' : 'light');
    }
    
    setMounted(true);
  }, []);  // [] = draait alleen bij eerste render

  // Wanneer theme verandert: update het HTML attribuut + localStorage
  useEffect(() => {
    if (mounted) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    }
  }, [theme, mounted]);  // Draait elke keer dat 'theme' verandert

  // Toggle functie: light → dark → light → ...
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Voorkom flash of wrong theme bij eerste render
  // (Server rendert altijd light, dan switcht client naar dark → flicker)
  if (!mounted) {
    return <div style={{ visibility: 'hidden' }}>{children}</div>;
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
