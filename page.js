'use client';

import { useTheme } from '../components/ThemeProvider';
import ThemeToggle from '../components/ThemeToggle';

export default function Home() {
  const { theme } = useTheme();

  return (
    <div style={{ minHeight: '100vh' }}>

      {/* ── HEADER ── */}
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        backgroundColor: theme === 'dark' 
          ? 'rgba(18, 17, 16, 0.85)' 
          : 'rgba(251, 248, 240, 0.85)',
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'all var(--transition-theme)',
      }}>
        <div style={{
          maxWidth: 'var(--max-width)',
          margin: '0 auto',
          padding: 'var(--space-4) var(--space-6)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span style={{
            fontFamily: 'var(--font-heading)',
            fontSize: 'var(--text-xl)',
            fontWeight: 600,
            color: 'var(--text-primary)',
            letterSpacing: 'var(--tracking-tight)',
          }}>
            randy<span style={{ color: 'var(--accent-primary)' }}>.</span>dev
          </span>
          
          <ThemeToggle />
        </div>
      </header>


      {/* ── HERO ── */}
      <section style={{
        padding: 'var(--space-32) var(--space-6)',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute',
          top: '-20%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, var(--accent-primary) 0%, transparent 70%)',
          opacity: 0.07,
          pointerEvents: 'none',
        }} />

        <p style={{
          fontFamily: 'var(--font-heading)',
          fontSize: 'var(--text-sm)',
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: 'var(--tracking-wider)',
          color: 'var(--accent-primary)',
          marginBottom: 'var(--space-6)',
        }}>
          Welcome to my corner of the internet
        </p>
        
        <h1 style={{
          fontSize: 'clamp(2.5rem, 6vw, 4rem)',
          fontWeight: 700,
          marginBottom: 'var(--space-6)',
          lineHeight: 1.1,
        }}>
          Ik bouw dingen<br />
          <span className="text-gradient">met code & creativiteit</span>
        </h1>
        
        <p style={{
          fontSize: 'var(--text-lg)',
          maxWidth: '560px',
          margin: '0 auto var(--space-8)',
          lineHeight: 'var(--leading-relaxed)',
        }}>
          Developer, maker, en eeuwige student. Dit is mijn 
          persoonlijke site — gebouwd van scratch om alles te leren.
        </p>
        
        <button style={{
          fontFamily: 'var(--font-heading)',
          fontSize: 'var(--text-sm)',
          fontWeight: 500,
          letterSpacing: 'var(--tracking-wide)',
          textTransform: 'uppercase',
          color: '#121110',
          backgroundColor: 'var(--accent-primary)',
          border: 'none',
          borderRadius: 'var(--radius-full)',
          padding: 'var(--space-4) var(--space-8)',
          cursor: 'pointer',
          transition: 'all var(--transition-base)',
          boxShadow: 'var(--shadow-md)',
        }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)';
            e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
            e.currentTarget.style.transform = 'translateY(-2px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--accent-primary)';
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          Bekijk mijn werk →
        </button>
      </section>


      {/* ── KLEUREN SHOWCASE ── */}
      <section style={{
        padding: 'var(--space-20) var(--space-6)',
        backgroundColor: 'var(--bg-secondary)',
        transition: 'background-color var(--transition-theme)',
      }}>
        <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto' }}>
          <SectionHeader 
            label="Theming systeem"
            title="Honey & smoke"
            description="Warm honinggoud met rokerig donkergrijs. Alle kleuren via CSS variabelen — verander één waarde, hele site past zich aan."
          />
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 'var(--space-4)',
            marginTop: 'var(--space-8)',
          }}>
            <ColorSwatch 
              name="Honinggoud" 
              variable="--accent-primary" 
              description="Signature kleur — knoppen, links, highlights"
            />
            <ColorSwatch 
              name="Donker goud" 
              variable="--accent-secondary" 
              description="Diepere variant — hover states, gradients"
            />
            <ColorSwatch 
              name="Oud goud" 
              variable="--accent-tertiary" 
              description="Subtiel accent — nummers, decoraties"
            />
            <ColorSwatch 
              name="Achtergrond" 
              variable="--bg-primary" 
              description="Rokerig zwart / warm crème"
            />
            <ColorSwatch 
              name="Tekst primary" 
              variable="--text-primary" 
              description="Hoofdtekst — warm wit / warm zwart"
            />
            <ColorSwatch 
              name="Surface" 
              variable="--bg-secondary" 
              description="Secties, kaarten, elevated surfaces"
            />
          </div>
        </div>
      </section>


      {/* ── TYPOGRAFIE ── */}
      <section style={{
        padding: 'var(--space-20) var(--space-6)',
      }}>
        <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto' }}>
          <SectionHeader 
            label="Typografie"
            title="Space Grotesk + Source Serif"
            description="Geometrisch modern voor headings, elegant serif voor body text."
          />
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 'var(--space-8)',
            marginTop: 'var(--space-8)',
          }}>
            <TypeCard
              fontFamily="var(--font-heading)"
              fontName="Space Grotesk"
              sample="The quick brown fox jumps over the lazy dog"
              usage="Headings, buttons, navigatie"
            />
            <TypeCard
              fontFamily="var(--font-body)"
              fontName="Source Serif 4"
              sample="The quick brown fox jumps over the lazy dog"
              usage="Body text, paragrafen, beschrijvingen"
            />
          </div>
          
          <div style={{
            marginTop: 'var(--space-12)',
            padding: 'var(--space-8)',
            backgroundColor: 'var(--surface-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-xl)',
            boxShadow: 'var(--shadow-sm)',
          }}>
            <h4 style={{ marginBottom: 'var(--space-6)' }}>Type scale</h4>
            {[
              { size: '--text-5xl', label: '3.052rem — Display' },
              { size: '--text-4xl', label: '2.441rem — H2' },
              { size: '--text-3xl', label: '1.953rem — H3' },
              { size: '--text-2xl', label: '1.563rem — H4' },
              { size: '--text-xl', label: '1.25rem — Large' },
              { size: '--text-base', label: '1rem — Body' },
              { size: '--text-sm', label: '0.875rem — Small' },
            ].map(({ size, label }) => (
              <div key={size} style={{
                display: 'flex',
                alignItems: 'baseline',
                gap: 'var(--space-4)',
                padding: 'var(--space-3) 0',
                borderBottom: '1px solid var(--border-subtle)',
              }}>
                <span style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: `var(${size})`,
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  lineHeight: 1.2,
                  whiteSpace: 'nowrap',
                }}>
                  Aa
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-muted)',
                }}>
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* ── PROJECT CARDS ── */}
      <section style={{
        padding: 'var(--space-20) var(--space-6)',
        backgroundColor: 'var(--bg-secondary)',
        transition: 'background-color var(--transition-theme)',
      }}>
        <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto' }}>
          <SectionHeader 
            label="Componenten"
            title="Kaarten & surfaces"
            description="Dezelfde variabelen, verschillende componenten. Alles past zich automatisch aan bij theme switch."
          />
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 'var(--space-6)',
            marginTop: 'var(--space-8)',
          }}>
            <ProjectCard
              number="01"
              title="RAG Chatbot"
              description="Een chatbot die PDF documenten kan doorzoeken met embeddings en vector search."
              tags={['Python', 'LangChain', 'ChromaDB']}
            />
            <ProjectCard
              number="02"
              title="Command Center"
              description="Persoonlijk dashboard met AI-briefings, weer, en task management."
              tags={['React', 'FastAPI', 'Claude API']}
            />
            <ProjectCard
              number="03"
              title="Deze Website"
              description="Gebouwd van scratch met Next.js. Custom theming, animaties, en meer."
              tags={['Next.js', 'CSS Variables', 'React']}
            />
          </div>
        </div>
      </section>


      {/* ── FOOTER ── */}
      <footer style={{
        padding: 'var(--space-12) var(--space-6)',
        textAlign: 'center',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        <p style={{
          fontFamily: 'var(--font-heading)',
          fontSize: 'var(--text-sm)',
          color: 'var(--text-muted)',
        }}>
          Gebouwd met Next.js & veel koffie — 2026
        </p>
      </footer>
    </div>
  );
}


/* ── HELPER COMPONENTEN ── */

function SectionHeader({ label, title, description }) {
  return (
    <div style={{ maxWidth: '600px' }}>
      <p style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 'var(--text-xs)',
        fontWeight: 500,
        textTransform: 'uppercase',
        letterSpacing: 'var(--tracking-wider)',
        color: 'var(--accent-primary)',
        marginBottom: 'var(--space-3)',
      }}>
        {label}
      </p>
      <h2 style={{
        fontSize: 'var(--text-3xl)',
        marginBottom: 'var(--space-4)',
      }}>
        {title}
      </h2>
      <p style={{ fontSize: 'var(--text-lg)' }}>
        {description}
      </p>
    </div>
  );
}

function ColorSwatch({ name, variable, description }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-card)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      boxShadow: 'var(--shadow-sm)',
      transition: 'all var(--transition-base)',
    }}>
      <div style={{
        height: '80px',
        backgroundColor: `var(${variable})`,
        transition: 'background-color var(--transition-theme)',
      }} />
      <div style={{ padding: 'var(--space-4)' }}>
        <p style={{
          fontFamily: 'var(--font-heading)',
          fontSize: 'var(--text-sm)',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: 'var(--space-1)',
        }}>
          {name}
        </p>
        <p style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-xs)',
          color: 'var(--accent-primary)',
          marginBottom: 'var(--space-2)',
        }}>
          var({variable})
        </p>
        <p style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-muted)',
          lineHeight: 'var(--leading-normal)',
        }}>
          {description}
        </p>
      </div>
    </div>
  );
}

function TypeCard({ fontFamily, fontName, sample, usage }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-card)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-xl)',
      padding: 'var(--space-8)',
      boxShadow: 'var(--shadow-sm)',
    }}>
      <p style={{
        fontFamily: fontFamily,
        fontSize: 'var(--text-4xl)',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: 'var(--space-2)',
      }}>
        {fontName}
      </p>
      <p style={{
        fontFamily: fontFamily,
        fontSize: 'var(--text-lg)',
        color: 'var(--text-secondary)',
        marginBottom: 'var(--space-4)',
        lineHeight: 'var(--leading-relaxed)',
      }}>
        {sample}
      </p>
      <p style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 'var(--text-xs)',
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: 'var(--tracking-wide)',
      }}>
        {usage}
      </p>
    </div>
  );
}

function ProjectCard({ number, title, description, tags }) {
  return (
    <div 
      style={{
        backgroundColor: 'var(--surface-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-xl)',
        padding: 'var(--space-8)',
        boxShadow: 'var(--shadow-sm)',
        transition: 'all var(--transition-base)',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--accent-primary)';
        e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
        e.currentTarget.style.transform = 'translateY(-4px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--border-subtle)';
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      <span style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 'var(--text-4xl)',
        fontWeight: 700,
        color: 'var(--accent-tertiary)',
        lineHeight: 1,
        opacity: 0.4,
      }}>
        {number}
      </span>
      
      <h3 style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 'var(--text-xl)',
        fontWeight: 600,
        marginTop: 'var(--space-4)',
        marginBottom: 'var(--space-3)',
      }}>
        {title}
      </h3>
      
      <p style={{
        fontSize: 'var(--text-sm)',
        marginBottom: 'var(--space-4)',
        lineHeight: 'var(--leading-relaxed)',
      }}>
        {description}
      </p>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        {tags.map(tag => (
          <span key={tag} style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--text-xs)',
            padding: 'var(--space-1) var(--space-3)',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--accent-primary)',
            border: '1px solid var(--border-subtle)',
          }}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}