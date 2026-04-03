/*
  ============================================
  ROOT LAYOUT
  ============================================
  
  In Next.js (App Router) is layout.js een speciaal bestand.
  Het "wraps" alle pagina's in dezelfde structuur.
  
  Denk aan het als een fotolijst: de layout is de lijst,
  de pagina (children) is de foto die wisselt.
  
  Dit is de PERFECTE plek voor:
  - Global CSS laden
  - ThemeProvider (zodat ALLE pagina's theme support hebben)
  - Metadata (titel, beschrijving voor Google)
  
  ============================================
*/

import '../styles/globals.css';
import ThemeProvider from '../components/ThemeProvider';

// Metadata — Next.js gebruikt dit voor de <title> en <meta> tags
// Dit is goed voor SEO (vindbaarheid in Google)
export const metadata = {
  title: 'Randy | Developer & Creator',
  description: 'Persoonlijke website en portfolio van Randy — projecten, blog, en meer.',
};

export default function RootLayout({ children }) {
  return (
    // defaultValue="light" voorkomt een FOUC (Flash of Unstyled Content)
    // Het script in ThemeProvider overschrijft dit direct bij laden
    <html lang="nl" data-theme="light" suppressHydrationWarning>
      <body>
        {/* ThemeProvider wraps ALLES — zo kan elk component 
            het theme opvragen met useTheme() */}
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
