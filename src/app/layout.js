import '../styles/globals.css';
import { ThemeProvider } from '../components/ThemeProvider';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import PageTransition from '../components/PageTransition';
import NetworkBackground from '../components/NetworkBackground';
import DataGrid from '../components/DataGrid';
import AuthProvider from '../components/AuthProvider';

export const metadata = {
  title: 'RDG. — Real Estate AI Automation',
  description: 'Randy de Groot — I build AI tools that automate real estate workflows.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="dark">
      <body style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <AuthProvider>
          <ThemeProvider>
            <DataGrid />
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
                background: 'linear-gradient(to bottom, var(--bg-primary) 0%, transparent 12%, transparent 88%, var(--bg-primary) 100%)',
              }}
            />
            <Navbar />
            <main style={{ flex: 1, overflowX: 'hidden', position: 'relative', zIndex: 6 }}>
              <PageTransition>{children}</PageTransition>
            </main>
            <Footer />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
