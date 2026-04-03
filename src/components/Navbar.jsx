'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';

const NAV_LINKS = [
  { label: 'Home',  href: '/' },
  { label: 'Work',  href: '/work' },
  { label: 'About', href: '/about' },
  { label: 'Blog',  href: '/blog' },
];

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [hoveredHref, setHoveredHref] = useState(null);

  /* Close menu on route change */
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  /* Lock body scroll while menu is open */
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  const isActive = href =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <>
      {/* ── responsive helpers ─────────────────────────── */}
      <style>{`
        .nav-desktop { display: flex; }
        .nav-hamburger { display: none; }
        @media (max-width: 767px) {
          .nav-desktop   { display: none; }
          .nav-hamburger { display: flex; }
        }
      `}</style>

      {/* ── sticky header ──────────────────────────────── */}
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
          backgroundColor: 'color-mix(in srgb, var(--bg-primary) 80%, transparent)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div
          className="container"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '4rem',
          }}
        >
          {/* Logo */}
          <Link
            href="/"
            style={{
              fontFamily: 'var(--font-heading)',
              fontWeight: 700,
              fontSize: 'var(--text-lg)',
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
              textDecoration: 'none',
            }}
          >
            randy<span style={{ color: 'var(--accent-primary)' }}>.</span>dev
          </Link>

          {/* Desktop nav */}
          <nav
            className="nav-desktop"
            style={{ alignItems: 'center', gap: 'var(--space-8)' }}
          >
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
                      fontSize: 'var(--text-sm)',
                      fontWeight: 500,
                      color: isActive(href) || hoveredHref === href
                        ? 'var(--text-primary)'
                        : 'var(--text-secondary)',
                      textDecoration: 'none',
                      display: 'block',
                      paddingBottom: 'var(--space-1)',
                      transition: 'color var(--transition-base)',
                    }}
                  >
                    {label}
                  </Link>

                  {/* Hover underline (non-active) */}
                  <AnimatePresence>
                    {hoveredHref === href && !isActive(href) && (
                      <motion.span
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        exit={{ scaleX: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        style={{
                          position: 'absolute',
                          bottom: 0,
                          left: 0,
                          right: 0,
                          height: '2px',
                          backgroundColor: 'var(--accent-primary)',
                          transformOrigin: 'left',
                        }}
                      />
                    )}
                  </AnimatePresence>

                  {/* Active underline — animates between links via layoutId */}
                  {isActive(href) && (
                    <motion.span
                      layoutId="nav-underline"
                      style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        height: '2px',
                        backgroundColor: 'var(--accent-primary)',
                      }}
                    />
                  )}
                </div>
              ))}
            </LayoutGroup>
            <ThemeToggle />
          </nav>

          {/* Mobile: ThemeToggle + hamburger */}
          <div
            className="nav-hamburger"
            style={{ alignItems: 'center', gap: 'var(--space-3)' }}
          >
            <ThemeToggle />
            <button
              aria-label={menuOpen ? 'Sluit menu' : 'Open menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(v => !v)}
              style={{
                width: '2.5rem',
                height: '2.5rem',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-default)',
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              {/* Three lines → X */}
              <span
                style={{
                  display: 'block',
                  width: '18px',
                  height: '2px',
                  backgroundColor: 'var(--text-primary)',
                  borderRadius: '2px',
                  transition: 'transform var(--transition-base), opacity var(--transition-base)',
                  transform: menuOpen ? 'translateY(7px) rotate(45deg)' : 'none',
                }}
              />
              <span
                style={{
                  display: 'block',
                  width: '18px',
                  height: '2px',
                  backgroundColor: 'var(--text-primary)',
                  borderRadius: '2px',
                  transition: 'opacity var(--transition-base)',
                  opacity: menuOpen ? 0 : 1,
                }}
              />
              <span
                style={{
                  display: 'block',
                  width: '18px',
                  height: '2px',
                  backgroundColor: 'var(--text-primary)',
                  borderRadius: '2px',
                  transition: 'transform var(--transition-base), opacity var(--transition-base)',
                  transform: menuOpen ? 'translateY(-7px) rotate(-45deg)' : 'none',
                }}
              />
            </button>
          </div>
        </div>
      </motion.header>

      {/* ── Mobile fullscreen overlay ───────────────────── */}
      {menuOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99,
            backgroundColor: 'var(--bg-primary)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
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
                fontWeight: 600,
                color: isActive(href) ? 'var(--accent-primary)' : 'var(--text-primary)',
                textDecoration: 'none',
                transition: 'color var(--transition-base)',
              }}
              onMouseEnter={e => {
                if (!isActive(href)) e.currentTarget.style.color = 'var(--accent-primary)';
              }}
              onMouseLeave={e => {
                if (!isActive(href)) e.currentTarget.style.color = 'var(--text-primary)';
              }}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
