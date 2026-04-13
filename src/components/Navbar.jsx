'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';

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

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

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
      `}</style>

      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          backgroundColor: 'color-mix(in srgb, var(--bg-primary) 85%, transparent)',
          borderBottom: '1px solid rgba(232,185,49,0.08)',
        }}
      >
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
