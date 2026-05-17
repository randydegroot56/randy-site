'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';
import { useTheme } from './ThemeProvider';

const NAV_LINKS = [
  { label: 'WORK',     href: '/work' },
  { label: 'AGENTS',   href: '/agents' },
  { label: 'ABOUT',    href: '/about' },
  { label: 'BLOG',     href: '/blog' },
  { label: 'CALENDAR', href: '/calendar' },
];

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [hoveredHref, setHoveredHref] = useState(null);
  const [scrolled, setScrolled] = useState(false);
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const isActive = href =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <>
      <style>{`
        .nav-desktop { display: flex; }
        .nav-hamburger { display: none; }
        @media (max-width: 767px) {
          .nav-desktop   { display: none; }
          .nav-hamburger { display: flex; }
        }
        @keyframes wifiPulse {
          0%, 100% { opacity: 0.2; }
          50% { opacity: 1; }
        }
        .wifi-dot  { animation: wifiPulse 2.4s ease-in-out infinite; animation-delay: 0s; }
        .wifi-arc1 { animation: wifiPulse 2.4s ease-in-out infinite; animation-delay: 0.3s; }
        .wifi-arc2 { animation: wifiPulse 2.4s ease-in-out infinite; animation-delay: 0.6s; }
        .wifi-arc3 { animation: wifiPulse 2.4s ease-in-out infinite; animation-delay: 0.9s; }
        @media (prefers-reduced-motion: reduce) {
          .wifi-dot, .wifi-arc1, .wifi-arc2, .wifi-arc3 { animation: none; opacity: 0.6; }
        }
      `}</style>

      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          transition: 'background-color 0.7s ease, border-color 0.7s ease, box-shadow 0.7s ease, backdrop-filter 0.7s ease',
          backdropFilter: scrolled ? 'blur(16px)' : 'none',
          WebkitBackdropFilter: scrolled ? 'blur(16px)' : 'none',
          backgroundColor: scrolled
            ? (isDark ? 'rgba(18,17,16,0.82)' : 'rgba(251,248,240,0.88)')
            : 'transparent',
          borderBottom: scrolled
            ? '1px solid rgba(232,185,49,0.15)'
            : '1px solid transparent',
          boxShadow: scrolled
            ? (isDark ? '0 1px 32px rgba(0,0,0,0.5)' : '0 1px 20px rgba(26,23,20,0.08)')
            : 'none',
        }}
      >
        {/* Vertical gold accent line */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            left: 0, top: 'var(--space-2)', bottom: 'var(--space-2)',
            width: '2px',
            background: 'linear-gradient(to bottom, transparent, #E8B931 35%, #E8B931 65%, transparent)',
            opacity: scrolled ? 1 : 0,
            transition: 'opacity 0.3s ease',
            pointerEvents: 'none',
          }}
        />
        <div
          className="container"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '4rem' }}
        >
          {/* Logo */}
          <Link
            href="/"
            style={{
              fontFamily: 'monospace',
              fontWeight: 700,
              fontSize: 'var(--text-lg)',
              color: 'var(--accent-primary)',
              letterSpacing: '0.05em',
              textDecoration: 'none',
              paddingLeft: 'var(--space-3)',
            }}
          >
            RDG<span style={{ color: 'rgba(232,185,49,0.4)' }}>.</span>
          </Link>

          {/* Desktop nav */}
          <nav className="nav-desktop" style={{ alignItems: 'center', gap: 'var(--space-8)' }}>
            <LayoutGroup>
              {NAV_LINKS.map(({ label, href }) => (
                <div
                  key={href}
                  style={{ position: 'relative' }}
                  onMouseEnter={() => setHoveredHref(href)}
                  onMouseLeave={() => setHoveredHref(null)}
                >
                  <Link
                    href={href}
                    style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      letterSpacing: '0.12em',
                      color: isActive(href) || hoveredHref === href
                        ? 'var(--accent-primary)'
                        : 'var(--text-secondary)',
                      textDecoration: 'none',
                      display: 'block',
                      paddingBottom: 'var(--space-1)',
                      transition: 'color var(--transition-base)',
                    }}
                  >
                    {label}
                  </Link>

                  <AnimatePresence>
                    {hoveredHref === href && !isActive(href) && (
                      <motion.span
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        exit={{ scaleX: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        style={{
                          position: 'absolute', bottom: 0, left: 0, right: 0,
                          height: '1px', backgroundColor: 'var(--accent-primary)',
                          transformOrigin: 'left',
                        }}
                      />
                    )}
                  </AnimatePresence>

                  {isActive(href) && (
                    <motion.span
                      layoutId="nav-underline"
                      style={{
                        position: 'absolute', bottom: 0, left: 0, right: 0,
                        height: '1px', backgroundColor: 'var(--accent-primary)',
                      }}
                    />
                  )}
                </div>
              ))}
            </LayoutGroup>

            {/* SYS.ONLINE badge — desktop only, fades in on scroll */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              fontFamily: 'monospace', fontSize: '8px', letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: isDark ? 'rgba(232,185,49,0.3)' : 'rgba(26,23,20,0.25)',
              opacity: scrolled ? 1 : 0,
              transition: 'opacity 0.3s ease',
              userSelect: 'none',
            }}>
              <svg
                width="13" height="11"
                viewBox="0 0 24 20"
                fill="none"
                aria-hidden="true"
                style={{ flexShrink: 0, display: 'inline-block' }}
              >
                <path className="wifi-arc3" d="M1.5 7.8a15 15 0 0 1 21 0" stroke="var(--accent-primary)" strokeWidth="2.2" strokeLinecap="round" />
                <path className="wifi-arc2" d="M5.2 11.6a10 10 0 0 1 13.6 0" stroke="var(--accent-primary)" strokeWidth="2.2" strokeLinecap="round" />
                <path className="wifi-arc1" d="M8.8 15.4a5 5 0 0 1 6.4 0" stroke="var(--accent-primary)" strokeWidth="2.2" strokeLinecap="round" />
                <circle className="wifi-dot" cx="12" cy="19" r="2" fill="var(--accent-primary)" />
              </svg>
              SYS.ONLINE
            </div>

            {/* Contact button */}
            <a
              href="mailto:hello@randy.dev"
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                padding: 'var(--space-2) var(--space-4)',
                border: '1px solid rgba(232,185,49,0.3)',
                transition: 'border-color var(--transition-fast), color var(--transition-fast)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                e.currentTarget.style.color = 'var(--accent-primary)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'rgba(232,185,49,0.3)';
                e.currentTarget.style.color = 'var(--accent-secondary)';
              }}
            >
              CONTACT
            </a>

            <ThemeToggle />
          </nav>

          {/* Mobile: ThemeToggle + hamburger */}
          <div className="nav-hamburger" style={{ alignItems: 'center', gap: 'var(--space-3)' }}>
            <ThemeToggle />
            <button
              aria-label={menuOpen ? 'Sluit menu' : 'Open menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(v => !v)}
              style={{
                width: '2.5rem', height: '2.5rem',
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: '5px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(232,185,49,0.2)',
                cursor: 'pointer', flexShrink: 0,
              }}
            >
              {[
                menuOpen ? 'translateY(7px) rotate(45deg)' : 'none',
                null,
                menuOpen ? 'translateY(-7px) rotate(-45deg)' : 'none',
              ].map((transform, i) => (
                <span
                  key={i}
                  style={{
                    display: 'block', width: '18px', height: '1px',
                    backgroundColor: 'var(--accent-primary)',
                    transition: 'transform var(--transition-base), opacity var(--transition-base)',
                    transform: transform || 'none',
                    opacity: i === 1 && menuOpen ? 0 : 1,
                  }}
                />
              ))}
            </button>
          </div>
        </div>
      </motion.header>

      {/* Mobile fullscreen overlay */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 99,
              backgroundColor: 'var(--bg-primary)',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              gap: 'var(--space-8)',
            }}
          >
            {NAV_LINKS.map(({ label, href }) => (
              <Link
                key={href}
                href={href}
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-2xl)',
                  fontWeight: 800,
                  letterSpacing: '0.06em',
                  color: isActive(href) ? 'var(--accent-primary)' : 'var(--text-primary)',
                  textDecoration: 'none',
                  transition: 'color var(--transition-base)',
                }}
                onMouseEnter={e => { if (!isActive(href)) e.currentTarget.style.color = 'var(--accent-primary)'; }}
                onMouseLeave={e => { if (!isActive(href)) e.currentTarget.style.color = 'var(--text-primary)'; }}
              >
                {label}
              </Link>
            ))}
            <a
              href="mailto:hello@randy.dev"
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: 'var(--text-base)',
                fontWeight: 600,
                letterSpacing: '0.12em',
                color: 'var(--accent-secondary)',
                textDecoration: 'none',
                padding: 'var(--space-3) var(--space-8)',
                border: '1px solid rgba(232,185,49,0.3)',
              }}
            >
              CONTACT
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
