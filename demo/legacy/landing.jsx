// Landing.jsx — CryptoAcademy landing page, parameterized by theme.
// Three colorways: greenDark, tealDark, cream. Each artboard renders
// a complete page (hero + how it works + footer).

const THEMES = {
  greenDark: {
    name: 'Eclipse',
    bg: '#080a09',
    bgAlt: '#0d100e',
    bgPanel: 'rgba(255,255,255,0.025)',
    fg: '#f1f3ee',
    fgSoft: '#c9cdc1',
    fgMuted: '#8b8e83',
    fgDim: '#5a5d54',
    accent: '#a8ee71',
    accentInk: '#0a1304',
    accentSoft: 'rgba(168,238,113,0.16)',
    glow: 'rgba(168,238,113,0.55)',
    line: 'rgba(255,255,255,0.07)',
    lineSoft: 'rgba(255,255,255,0.04)',
    coinTint: 'none',
    gridDot: 'rgba(255,255,255,0.05)',
  },
  tealDark: {
    name: 'Tidewater',
    bg: '#06090d',
    bgAlt: '#0a1219',
    bgPanel: 'rgba(255,255,255,0.025)',
    fg: '#eff4f7',
    fgSoft: '#c5cdd5',
    fgMuted: '#838d97',
    fgDim: '#525a63',
    accent: '#5eead4',
    accentInk: '#04130f',
    accentSoft: 'rgba(94,234,212,0.14)',
    glow: 'rgba(94,234,212,0.55)',
    line: 'rgba(255,255,255,0.07)',
    lineSoft: 'rgba(255,255,255,0.04)',
    coinTint: 'none',
    gridDot: 'rgba(255,255,255,0.05)',
  },
  cream: {
    name: 'Bone',
    bg: '#f1ece0',
    bgAlt: '#e6dfcf',
    bgPanel: 'rgba(20,15,10,0.035)',
    fg: '#12100c',
    fgSoft: '#33302a',
    fgMuted: '#6b6557',
    fgDim: '#9a9384',
    accent: '#161310',
    accentInk: '#f1ece0',
    accentSoft: 'rgba(20,15,10,0.06)',
    glow: 'rgba(196,148,72,0.35)',
    line: 'rgba(20,15,10,0.11)',
    lineSoft: 'rgba(20,15,10,0.06)',
    coinTint: 'none',
    gridDot: 'rgba(20,15,10,0.08)',
  },
};

// ─── small atoms ─────────────────────────────────────────────────────────
function Logo({ t }) {
  return (
    <a href="index.html" style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'var(--ca-display)', fontWeight: 600, fontSize: 17, letterSpacing: '-0.01em', color: t.fg, textDecoration: 'none' }}>
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="10" stroke={t.fg} strokeWidth="1.4" />
        <path d="M11 4 L17 11 L11 18 L5 11 Z" stroke={t.fg} strokeWidth="1.4" fill="none" />
        <circle cx="11" cy="11" r="2.4" fill={t.accent} />
      </svg>
      CryptoAcademy
    </a>
  );
}

function Nav({ t, active }) {
  const links = [
    ['Courses', 'courses.html'],
    ['ML Model', 'ml-model.html'],
    ['Daily Reports', 'daily-reports.html'],
  ];
  return (
    <nav style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '26px 56px', borderBottom: `1px solid ${t.line}`,
      position: 'relative', zIndex: 5,
    }}>
      <Logo t={t} />
      <div style={{ display: 'flex', gap: 32, fontSize: 14, fontFamily: 'var(--ca-display)', letterSpacing: '-0.005em' }}>
        {links.map(([label, href]) => {
          const isActive = label === active;
          return (
            <a key={label} href={href} style={{
              color: isActive ? t.fg : t.fgSoft,
              textDecoration: 'none', cursor: 'pointer',
              position: 'relative', paddingBottom: 4,
            }}>
              {label}
              {isActive && (
                <span style={{
                  position: 'absolute', left: 0, right: 0, bottom: -1,
                  height: 1.5, background: t.accent,
                  boxShadow: `0 0 8px ${t.accent}`,
                }} />
              )}
            </a>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <a href="#signin" style={{ fontSize: 14, color: t.fgSoft, fontFamily: 'var(--ca-display)', cursor: 'pointer', textDecoration: 'none' }}>Sign in</a>
        <a href="courses.html" style={{
          background: t.accent, color: t.accentInk, border: 'none',
          padding: '10px 18px', borderRadius: 999, fontFamily: 'var(--ca-display)',
          fontSize: 14, fontWeight: 500, letterSpacing: '-0.005em', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6, textDecoration: 'none',
        }}>
          Enroll <span style={{ fontSize: 16, lineHeight: 1 }}>→</span>
        </a>
      </div>
    </nav>
  );
}

// Tag chip e.g. "● LIVE COHORT · FALL 2026"
function Eyebrow({ t, dotColor }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 10,
      padding: '7px 14px 7px 12px', borderRadius: 999,
      border: `1px solid ${t.line}`, background: t.bgPanel,
      fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.14em',
      color: t.fgSoft, textTransform: 'uppercase',
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: 999,
        background: dotColor || t.accent,
        boxShadow: `0 0 8px ${dotColor || t.accent}`,
      }} />
      Live cohort · Fall 2026 · 142 / 180 seats
    </div>
  );
}

// Hero block. Title is split across the coin: "CRYPTO" above, coin, "ACADEMY" below.
function Hero({ t, themeKey }) {
  const coinSize = 460;
  return (
    <section style={{ position: 'relative', padding: '64px 56px 90px', overflow: 'hidden' }}>
      {/* radial backdrop */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse 60% 50% at 50% 48%, ${t.accentSoft} 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />
      {/* faint dot grid */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `radial-gradient(${t.gridDot} 1px, transparent 1px)`,
        backgroundSize: '28px 28px',
        maskImage: 'radial-gradient(ellipse 70% 60% at 50% 50%, black 30%, transparent 80%)',
        WebkitMaskImage: 'radial-gradient(ellipse 70% 60% at 50% 50%, black 30%, transparent 80%)',
        pointerEvents: 'none', opacity: 0.6,
      }} />

      {/* Title with coin in middle */}
      <div style={{ position: 'relative', textAlign: 'center' }}>
        <h1 style={{
          margin: 0, padding: 0,
          fontFamily: 'var(--ca-display)',
          fontWeight: 500,
          fontSize: 196,
          lineHeight: 0.92,
          letterSpacing: '-0.045em',
          color: t.fg,
        }}>
          <div className="ca-word-up" style={{ animationDelay: '0.15s' }}>Crypto</div>
          <div style={{ position: 'relative', height: coinSize, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            {/* glow */}
            <div className="ca-pulse" style={{
              position: 'absolute', width: coinSize * 1.15, height: coinSize * 1.15,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${t.glow} 0%, transparent 62%)`,
              filter: 'blur(10px)',
              pointerEvents: 'none',
            }} />
            {/* rotating ring marks */}
            <svg className="ca-ring-spin" width={coinSize * 1.32} height={coinSize * 1.32} viewBox="0 0 100 100" style={{
              position: 'absolute', pointerEvents: 'none', opacity: 0.45,
            }}>
              <circle cx="50" cy="50" r="48" fill="none" stroke={t.line} strokeWidth="0.2" strokeDasharray="0.6 1.4" />
              <circle cx="50" cy="50" r="44" fill="none" stroke={t.line} strokeWidth="0.15" strokeDasharray="0.3 3" />
            </svg>
            {/* coin */}
            <div className="ca-coin-scale" style={{ width: coinSize, height: coinSize, position: 'relative' }}>
              <div className="ca-coin-float" style={{ width: '100%', height: '100%' }}>
                <div className="ca-coin-tilt" style={{ width: '100%', height: '100%' }}>
                  <img src="assets/coin.png" alt="" style={{
                    width: '100%', height: '100%', objectFit: 'contain',
                    filter: themeKey === 'cream'
                      ? 'drop-shadow(0 30px 60px rgba(120,80,30,0.35)) drop-shadow(0 8px 16px rgba(80,50,20,0.25))'
                      : 'drop-shadow(0 30px 60px rgba(0,0,0,0.55)) drop-shadow(0 0 30px rgba(255,180,80,0.18))',
                  }} />
                </div>
              </div>
            </div>
          </div>
          <div className="ca-word-up" style={{ animationDelay: '0.35s' }}>Academy</div>
        </h1>
      </div>

      {/* Sublabel + CTAs */}
      <div className="ca-fade-in" style={{ animationDelay: '0.7s', position: 'relative', marginTop: 56, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        <p style={{
          margin: 0, maxWidth: 640, textAlign: 'center',
          fontFamily: 'var(--ca-display)', fontSize: 19, lineHeight: 1.45,
          color: t.fgSoft, letterSpacing: '-0.005em',
        }}>
          A complete technical-analysis course for BTC and ETH. Learn how
          the market really moves — supported by a live ML model and a daily,
          model-generated brief built in-house for our students.
        </p>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <a href="courses.html" style={{
            background: t.accent, color: t.accentInk, border: 'none',
            padding: '14px 22px', borderRadius: 999, fontFamily: 'var(--ca-display)',
            fontSize: 15, fontWeight: 500, letterSpacing: '-0.005em', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none',
          }}>
            Enroll · Fall 2026
            <span style={{ fontSize: 17, lineHeight: 1 }}>→</span>
          </a>
          <a href="daily-reports.html" style={{
            background: 'transparent', color: t.fg, border: `1px solid ${t.line}`,
            padding: '14px 20px', borderRadius: 999, fontFamily: 'var(--ca-display)',
            fontSize: 15, fontWeight: 500, letterSpacing: '-0.005em', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none',
          }}>
            Read today's brief
            <span style={{ fontSize: 14, opacity: 0.7 }}>↗</span>
          </a>
        </div>
      </div>
    </section>
  );
}

// Live-data style ticker
function Ticker({ t }) {
  const rows = [
    ['BTC / USD', '67,420.18', '+2.31%', true],
    ['ETH / USD', '3,512.40', '+1.04%', true],
    ['Model bias', 'long ·  72%', '24h', null],
    ['Sentiment', 'risk-on', '+0.41', true],
    ['Signals issued', '14', 'today', null],
  ];
  const cell = (i) => {
    const [a, b, c, up] = rows[i];
    const color = up === null ? t.fgMuted : up ? t.accent : '#ef6464';
    return (
      <div key={i} style={{
        flex: 1, padding: '20px 26px', borderRight: i < rows.length - 1 ? `1px solid ${t.line}` : 'none',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <span style={{ fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.14em', color: t.fgMuted, textTransform: 'uppercase' }}>{a}</span>
        <span style={{ fontFamily: 'var(--ca-mono)', fontSize: 22, color: t.fg, letterSpacing: '-0.01em' }}>{b}</span>
        <span style={{ fontFamily: 'var(--ca-mono)', fontSize: 11, color }}>{c}</span>
      </div>
    );
  };
  return (
    <div style={{
      margin: '0 56px', display: 'flex', alignItems: 'stretch',
      borderTop: `1px solid ${t.line}`, borderBottom: `1px solid ${t.line}`,
      background: t.bgPanel,
    }}>
      {rows.map((_, i) => cell(i))}
    </div>
  );
}

// Section heading: small label + big sentence
function SectionHead({ t, kicker, title, sub }) {
  return (
    <div style={{ padding: '110px 56px 50px', maxWidth: 1100 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
        color: t.fgMuted, textTransform: 'uppercase', marginBottom: 26,
      }}>
        <span style={{ width: 22, height: 1, background: t.fgMuted }} />
        {kicker}
      </div>
      <h2 style={{
        margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
        fontSize: 72, lineHeight: 1.02, letterSpacing: '-0.035em', color: t.fg,
        textWrap: 'balance', maxWidth: 960,
      }}>{title}</h2>
      {sub && (
        <p style={{
          margin: '24px 0 0', maxWidth: 620, fontFamily: 'var(--ca-display)',
          fontSize: 17, lineHeight: 1.5, color: t.fgSoft,
        }}>{sub}</p>
      )}
    </div>
  );
}

// Step card for "how it works"
function Step({ t, n, title, body, detail, accentNum }) {
  return (
    <div style={{
      flex: 1, padding: '28px 28px 32px',
      border: `1px solid ${t.line}`, borderRadius: 18,
      background: t.bgPanel, position: 'relative', overflow: 'hidden',
      display: 'flex', flexDirection: 'column', minHeight: 360,
    }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
        marginBottom: 24,
      }}>
        <span style={{
          fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.16em',
          color: t.fgMuted, textTransform: 'uppercase',
        }}>Step / {n}</span>
        <span style={{
          fontFamily: 'var(--ca-display)', fontSize: 56, fontWeight: 400,
          color: accentNum ? t.accent : t.fgDim, letterSpacing: '-0.04em',
          lineHeight: 0.9,
        }}>{n}</span>
      </div>
      <h3 style={{
        margin: 0, fontFamily: 'var(--ca-display)', fontSize: 26, fontWeight: 500,
        letterSpacing: '-0.02em', color: t.fg, lineHeight: 1.1,
      }}>{title}</h3>
      <p style={{
        margin: '14px 0 0', fontFamily: 'var(--ca-display)', fontSize: 14.5,
        lineHeight: 1.55, color: t.fgSoft,
      }}>{body}</p>
      <div style={{ flex: 1 }} />
      <div style={{
        marginTop: 20, paddingTop: 18,
        borderTop: `1px dashed ${t.line}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        fontFamily: 'var(--ca-mono)', fontSize: 11, color: t.fgMuted,
        letterSpacing: '0.04em',
      }}>
        <span>{detail.label}</span>
        <span style={{ color: t.fg }}>{detail.value}</span>
      </div>
    </div>
  );
}

function HowItWorks({ t }) {
  const steps = [
    {
      n: '01', accentNum: true, title: 'Learn the chart',
      body: 'Ten modules of pure technical analysis — structure, levels, indicators, liquidity, edge. Taught the way professional analysts read the market. No programming required.',
      detail: { label: 'Modules', value: '10 · two tiers' },
    },
    {
      n: '02', title: 'Practice on BTC and ETH',
      body: 'Live charts and case studies focused on the two assets you actually trade. Apply what you learn module by module, with a weekly walkthrough from the team.',
      detail: { label: 'Markets', value: 'BTC · ETH' },
    },
    {
      n: '03', title: 'Reference the model',
      body: 'Access the platform\'s in-house ML model. Read its directional bias and confidence for the day — a second opinion on your own analysis, never a replacement for it.',
      detail: { label: 'Refresh', value: 'Per candle close' },
    },
    {
      n: '04', title: 'Read the daily brief',
      body: 'A short, model-generated market overview is published every morning. Sentiment summary, risk flags, watchlist — to start your session informed.',
      detail: { label: 'Delivered', value: '07:00 UTC' },
    },
  ];
  return (
    <section style={{ position: 'relative' }}>
      <SectionHead
        t={t}
        kicker="How it works"
        title="A focused course, with tools built for our students."
        sub="The course teaches technical analysis — the theory of reading the market. The model and the daily brief are tools we built in-house, given to students so they spend their time on what matters: reading the chart."
      />
      <div style={{ display: 'flex', gap: 18, padding: '0 56px 80px' }}>
        {steps.map((s) => <Step key={s.n} t={t} {...s} />)}
      </div>
    </section>
  );
}

function Footer({ t }) {
  return (
    <footer style={{
      borderTop: `1px solid ${t.line}`,
      padding: '40px 56px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.12em',
      color: t.fgMuted, textTransform: 'uppercase',
    }}>
      <div style={{ display: 'flex', gap: 32 }}>
        <span>CryptoAcademy · Thesis demo · 2026</span>
      </div>
      <div style={{ display: 'flex', gap: 32 }}>
        <span>Theme · {t.name}</span>
        <span>v 0.4.2</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 6, height: 6, borderRadius: 999, background: t.accent, boxShadow: `0 0 8px ${t.accent}` }} />
          Model online
        </span>
      </div>
    </footer>
  );
}

function Landing({ themeKey }) {
  const t = THEMES[themeKey];
  return (
    <div style={{
      width: '100%', minHeight: '100%', background: t.bg, color: t.fg,
      fontFamily: 'var(--ca-display)',
      position: 'relative', overflow: 'hidden',
    }}>
      <Nav t={t} />
      <Hero t={t} themeKey={themeKey} />
      <Ticker t={t} />
      <HowItWorks t={t} />
      <Footer t={t} />
    </div>
  );
}

Object.assign(window, { Landing, Nav, Footer, Logo, Eyebrow, THEMES });
