import '../styles/globals.css';
import { ThemeProvider } from '../components/ThemeProvider';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import PageTransition from '../components/PageTransition';
import NetworkBackground from '../components/NetworkBackground';

export const metadata = {
  title: 'randy.dev',
  description: 'Portfolio van Randy — full-stack developer gespecialiseerd in AI-gedreven applicaties.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="nl" data-theme="light">
      <body
        style={{
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
        }}
      >
        <ThemeProvider>
          <NetworkBackground
            nodeColor="#E8B931"
            pulseColor="#C49A1A"
            bgColor="transparent"
          />
          <div
            aria-hidden="true"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 5,
              pointerEvents: 'none',
              background: 'linear-gradient(to bottom, var(--bg-primary) 0%, transparent 10%, transparent 90%, var(--bg-primary) 100%)',
            }}
          />
          <Navbar />
          <main style={{ flex: 1, overflowX: 'hidden' }}>
            <PageTransition>{children}</PageTransition>
          </main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
