// Courses.jsx — CryptoAcademy curriculum page.
// Same Eclipse theme. Three tone variations passed via prop:
//   - 'academic' : precise, restrained, thesis-style
//   - 'mix'      : credible academic + polished marketing
//   - 'premium'  : aspirational, like the landing

const TONE = {
  academic: {
    eyebrow: 'Curriculum',
    title: 'A structured curriculum in technical analysis.',
    sub: 'Ten sequenced modules organised into two tiers. Students progress from instrument literacy to systematic analysis using only chart-based methods. No programming is required.',
    cta: 'Apply to enrol',
    secCta: 'Request the syllabus',
    tier1Label: 'Tier I',
    tier1Name: 'Foundations',
    tier1Lead: 'Five modules covering the literacy and vocabulary of technical analysis. By the end of this tier students can read a chart, identify structure, and size a position responsibly.',
    tier2Label: 'Tier II',
    tier2Name: 'Advanced practice',
    tier2Lead: 'Five modules formalising the analyst’s toolkit. Phase analysis, volume reading, liquidity, multi-timeframe confluence, and the formal construction of a personal edge.',
    deepDiveKicker: 'Module sample',
    deepDive1Lead: 'The first module of Tier I, reproduced in full. Lessons proceed from chart anatomy to volume interpretation. Each lesson includes an annotated case study and a short formative exercise.',
    deepDive2Lead: 'The first module of Tier II, reproduced in full. Phase analysis is treated as the spine of the advanced track — every subsequent module returns to it.',
    deliverableLabel: 'Assessed deliverable',
    formatKicker: 'Programme format',
    formatTitle: 'How the material is delivered.',
    enrollTitle: 'Applications for the autumn cohort are open.',
    enrollSub: 'A short written application. Decisions within seven days. No coding background required; trading experience is welcomed but not assumed.',
  },
  mix: {
    eyebrow: 'The curriculum',
    title: 'Ten modules. One serious framework for reading the market.',
    sub: 'A complete technical analysis program built from the ground up. You start with how a chart works and finish with a personal trading playbook. No code, no fluff — just the practice.',
    cta: 'Reserve your seat',
    secCta: 'Download the syllabus',
    tier1Label: 'Track 01',
    tier1Name: 'Foundations',
    tier1Lead: 'Five modules that take you from your first candle to a full read of market structure. By the end you can look at a chart and understand what it’s telling you.',
    tier2Label: 'Track 02',
    tier2Name: 'Mastery',
    tier2Lead: 'Five modules covering the way professional analysts actually work. Phases, volume, liquidity, and the systems that turn analysis into edge.',
    deepDiveKicker: 'Sample module',
    deepDive1Lead: 'A complete look at the first Foundations module. Seven lessons walk you from raw candle anatomy to reading volume on a chart, with one assessed deliverable at the end.',
    deepDive2Lead: 'A complete look at the first Mastery module. Wyckoff phase analysis is the backbone of the advanced track — every later module loops back to it.',
    deliverableLabel: 'Deliverable',
    formatKicker: 'How it works',
    formatTitle: 'Built for steady, honest practice.',
    enrollTitle: 'The autumn cohort starts soon.',
    enrollSub: 'A short application form, a quick chat, then in. No prior coding required, no trading background assumed.',
  },
  premium: {
    eyebrow: 'Learn the chart',
    title: 'Read the market like a desk does.',
    sub: 'Ten modules that take you from your first candle to a working personal playbook. Patterns, structure, liquidity, edge — taught the way professionals see them.',
    cta: 'Take your seat',
    secCta: 'See the syllabus',
    tier1Label: 'I',
    tier1Name: 'Foundations',
    tier1Lead: 'Where every great trader starts. Five modules to make a chart legible — candles, structure, levels, and the discipline of risk.',
    tier2Label: 'II',
    tier2Name: 'Mastery',
    tier2Lead: 'How the pros actually look at the market. Phases, order flow, liquidity, confluence — the tools that separate analysis from edge.',
    deepDiveKicker: 'A module, opened up',
    deepDive1Lead: 'A complete walkthrough of the first Foundations module. Seven lessons. One annotated chart you’ll be proud to keep.',
    deepDive2Lead: 'A complete walkthrough of the first Mastery module. Phase analysis is the spine of the advanced track — once it clicks, the rest follows.',
    deliverableLabel: 'You’ll leave with',
    formatKicker: 'The format',
    formatTitle: 'Designed for the way real practice happens.',
    enrollTitle: 'Take your seat in the autumn cohort.',
    enrollSub: 'A short application, a quick conversation, and you’re in. No coding background, no trading experience required.',
  },
};

const MODULES = {
  beginner: [
    { n: 'B·01', title: 'Reading the Chart',        summary: 'Candles, time frames, and basic price action.' },
    { n: 'B·02', title: 'Trend & Structure',        summary: 'Swing points, higher highs and lower lows, market structure.' },
    { n: 'B·03', title: 'Support & Resistance',     summary: 'Levels, supply and demand zones, and how price reacts.' },
    { n: 'B·04', title: 'Core Indicators',          summary: 'Moving averages, RSI, and MACD without the noise.' },
    { n: 'B·05', title: 'Risk & Position Sizing',   summary: 'Stops, R-multiples, and the trading journal.' },
  ],
  advanced: [
    { n: 'A·01', title: 'Market Phases & Wyckoff',  summary: 'Accumulation, distribution, springs and upthrusts.' },
    { n: 'A·02', title: 'Volume Profile & Order Flow', summary: 'VPVR, footprint, delta, and absorption.' },
    { n: 'A·03', title: 'Liquidity & Smart Money',  summary: 'Order blocks, fair value gaps, and liquidity sweeps.' },
    { n: 'A·04', title: 'Multi-Timeframe Confluence', summary: 'Top-down analysis, alignment, and entry timing.' },
    { n: 'A·05', title: 'Building Your Edge',       summary: 'Systemising setups, expectancy, drawdown discipline.' },
  ],
};

const DEEP_DIVES = {
  beginner: {
    code: 'B·01',
    title: 'Reading the Chart',
    intro: 'Before any indicator, before any theory, there is the chart. This module rebuilds the relationship between a trader and the screen, one candle at a time.',
    lessons: [
      'The candlestick anatomy — open, high, low, close',
      'Time frames and what each one is telling you',
      'Single-candle patterns: hammers, pins, dojis',
      'Two- and three-candle reversals',
      'Volume as confirmation, not decoration',
      'Common chart artefacts to filter out',
      'Tools, drawings, and chart hygiene',
    ],
    deliverable: 'An annotated chart of a market of your choice, marked up to instructor standard.',
    stats: [
      { k: 'Lessons',  v: '7' },
      { k: 'Format',   v: 'Video + cases' },
      { k: 'Practice', v: '4 chart exercises' },
    ],
  },
  advanced: {
    code: 'A·01',
    title: 'Market Phases & Wyckoff',
    intro: 'Markets do not trend forever — they accumulate, distribute, and reset. This module installs the lens through which every later module is taught.',
    lessons: [
      'Why the market moves in phases',
      'Accumulation: signs, schematics, and tells',
      'Distribution: signs, schematics, and tells',
      'The Spring and the Upthrust',
      'Re-accumulation and re-distribution',
      'Effort vs. result — reading volume inside a phase',
      'Mapping a live BTC structure end-to-end',
    ],
    deliverable: 'A current-market phase report with rationale, key levels, and an invalidation thesis.',
    stats: [
      { k: 'Lessons',  v: '7' },
      { k: 'Format',   v: 'Video + live walkthrough' },
      { k: 'Practice', v: '3 phase reports' },
    ],
  },
};

const FORMAT = [
  { label: 'Video lessons',         body: 'Self-paced, fully captioned, with downloadable annotated charts.' },
  { label: 'Live chart walkthroughs', body: 'Weekly sessions where instructors mark up the week’s BTC and ETH action with the cohort.' },
  { label: 'Case studies',          body: 'Real historic setups dissected end-to-end — entry, management, exit, lesson.' },
  { label: 'Trading journal',       body: 'A structured template you’ll use to log every observation and trade you take.' },
  { label: 'Cohort discussion',     body: 'Private channels with peers and graduates from previous cohorts.' },
  { label: 'Capstone',              body: 'Your own trading playbook — written, annotated, and reviewed before you graduate.' },
];

// ─── components ──────────────────────────────────────────────────────────

const OUTCOMES = [
  'Read price action across multiple timeframes with consistency.',
  'Identify and classify market structure — trend, range, accumulation, distribution.',
  'Apply support, resistance, and zone-based analysis to live charts.',
  'Use core indicators meaningfully, without dependence on them.',
  'Diagnose volume behaviour and reconcile it with price action.',
  'Interpret liquidity dynamics and order-flow concepts.',
  'Recognise smart-money footprints: order blocks, fair value gaps, sweeps.',
  'Construct multi-timeframe analyses with internal consistency.',
  'Define, journal, and refine a personal trading edge.',
  'Maintain a complete, evidence-based trading playbook.',
];

const ASSESSMENT = [
  { k: 'Per module',     v: 'Annotated chart deliverable' },
  { k: 'Capstone',       v: 'Personal trading playbook' },
  { k: 'Cohort review',  v: 'Peer + instructor feedback' },
  { k: 'Pass criterion', v: 'Reasoned, defensible analysis' },
];

function PageHero({ t, c }) {
  return (
    <section style={{ padding: '92px 56px 70px', position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse 70% 50% at 20% 30%, ${t.accentSoft} 0%, transparent 65%)`,
        pointerEvents: 'none',
      }} />
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
        color: t.fgMuted, textTransform: 'uppercase', marginBottom: 28,
        position: 'relative',
      }}>
        <span style={{ width: 22, height: 1, background: t.fgMuted }} />
        {c.eyebrow}
      </div>
      <div style={{ display: 'flex', gap: 60, alignItems: 'flex-end', position: 'relative' }}>
        <h1 style={{
          margin: 0, flex: 1, fontFamily: 'var(--ca-display)',
          fontWeight: 500, fontSize: 88, lineHeight: 1.0,
          letterSpacing: '-0.035em', color: t.fg, textWrap: 'balance',
          maxWidth: 920,
        }}>{c.title}</h1>
        <div style={{ flex: '0 0 380px', paddingBottom: 14 }}>
          <p style={{
            margin: 0, fontFamily: 'var(--ca-display)', fontSize: 16,
            lineHeight: 1.6, color: t.fgSoft,
          }}>{c.sub}</p>
        </div>
      </div>
      {/* compact summary band */}
      <div style={{
        marginTop: 56, display: 'flex', borderTop: `1px solid ${t.line}`,
        borderBottom: `1px solid ${t.line}`,
      }}>
        {[
          ['Modules', '10'],
          ['Tiers', 'Foundations · Mastery'],
          ['Prerequisite', 'None'],
          ['Code', 'Not required'],
          ['Cohort', 'Autumn 2026'],
        ].map(([k, v], i, arr) => (
          <div key={k} style={{
            flex: 1, padding: '22px 26px',
            borderRight: i < arr.length - 1 ? `1px solid ${t.line}` : 'none',
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <span style={{ fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em', color: t.fgMuted, textTransform: 'uppercase' }}>{k}</span>
            <span style={{ fontFamily: 'var(--ca-display)', fontSize: 20, color: t.fg, letterSpacing: '-0.01em' }}>{v}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function TrackHeader({ t, label, name, lead }) {
  return (
    <div style={{ padding: '70px 56px 30px', display: 'flex', gap: 60, alignItems: 'flex-end' }}>
      <div style={{
        fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.2em',
        color: t.fgMuted, textTransform: 'uppercase',
        flex: '0 0 auto', paddingBottom: 12,
      }}>
        Track · {label}
      </div>
      <h2 style={{
        margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
        fontSize: 56, lineHeight: 1, letterSpacing: '-0.035em', color: t.fg,
        flex: '0 0 auto',
      }}>{name}</h2>
      <p style={{
        margin: 0, paddingBottom: 8, flex: 1, maxWidth: 520,
        fontFamily: 'var(--ca-display)', fontSize: 15, lineHeight: 1.55,
        color: t.fgSoft, textAlign: 'right',
      }}>{lead}</p>
    </div>
  );
}

function ModuleCard({ t, m, highlighted }) {
  return (
    <div className="courses-modulecard" style={{
      flex: 1, padding: '22px 22px 26px',
      border: `1px solid ${highlighted ? t.accent : t.line}`,
      borderRadius: 14,
      background: highlighted ? t.accentSoft : t.bgPanel,
      position: 'relative', overflow: 'hidden',
      display: 'flex', flexDirection: 'column', minHeight: 220,
      transition: 'transform .25s cubic-bezier(.2,.8,.2,1), border-color .25s, background .25s',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 28,
      }}>
        <span style={{
          fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.12em',
          color: highlighted ? t.accent : t.fgMuted,
        }}>{m.n}</span>
        {highlighted && (
          <span style={{
            fontFamily: 'var(--ca-mono)', fontSize: 9, letterSpacing: '0.16em',
            color: t.accent, textTransform: 'uppercase',
            padding: '3px 7px', border: `1px solid ${t.accent}`,
            borderRadius: 4,
          }}>Sample</span>
        )}
      </div>
      <h3 style={{
        margin: 0, fontFamily: 'var(--ca-display)', fontSize: 21, fontWeight: 500,
        letterSpacing: '-0.018em', color: t.fg, lineHeight: 1.15,
      }}>{m.title}</h3>
      <p style={{
        margin: '12px 0 0', fontFamily: 'var(--ca-display)', fontSize: 13.5,
        lineHeight: 1.5, color: t.fgSoft,
      }}>{m.summary}</p>
      <div style={{ flex: 1 }} />
      <div style={{
        marginTop: 18, display: 'flex', alignItems: 'center', gap: 8,
        fontFamily: 'var(--ca-mono)', fontSize: 10, color: t.fgMuted,
        letterSpacing: '0.1em', textTransform: 'uppercase',
      }}>
        <span style={{ width: 14, height: 1, background: t.fgMuted }} />
        Module
      </div>
    </div>
  );
}

function ModuleRow({ t, modules, highlightFirst }) {
  return (
    <div style={{ display: 'flex', gap: 14, padding: '0 56px' }}>
      {modules.map((m, i) => (
        <ModuleCard key={m.n} t={t} m={m} highlighted={highlightFirst && i === 0} />
      ))}
    </div>
  );
}

function DeepDive({ t, c, dive, lead, secCta }) {
  return (
    <section style={{ padding: '60px 56px 0' }}>
      <div style={{
        border: `1px solid ${t.line}`, borderRadius: 22,
        background: t.bgPanel, position: 'relative', overflow: 'hidden',
      }}>
        {/* accent corner */}
        <div style={{
          position: 'absolute', top: 0, right: 0, width: 220, height: 220,
          background: `radial-gradient(circle at 100% 0%, ${t.accentSoft} 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />
        <div style={{ display: 'flex', position: 'relative' }}>
          {/* Left column */}
          <div style={{ flex: '1.1 1 0', padding: '46px 48px 46px', borderRight: `1px solid ${t.line}` }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.16em',
              color: t.accent, textTransform: 'uppercase', marginBottom: 26,
            }}>
              <span style={{ width: 7, height: 7, borderRadius: 999, background: t.accent, boxShadow: `0 0 8px ${t.accent}` }} />
              {c.deepDiveKicker} · {dive.code}
            </div>
            <h3 style={{
              margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
              fontSize: 52, lineHeight: 1.02, letterSpacing: '-0.03em', color: t.fg,
              textWrap: 'balance',
            }}>{dive.title}</h3>
            <p style={{
              margin: '22px 0 0', maxWidth: 460,
              fontFamily: 'var(--ca-display)', fontSize: 16, lineHeight: 1.55,
              color: t.fgSoft,
            }}>{lead}</p>
            <div style={{
              marginTop: 36, padding: '22px 24px',
              border: `1px solid ${t.line}`, borderRadius: 14,
              background: t.bg,
            }}>
              <div style={{
                fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
                color: t.fgMuted, textTransform: 'uppercase', marginBottom: 10,
              }}>{c.deliverableLabel}</div>
              <div style={{
                fontFamily: 'var(--ca-display)', fontSize: 16, lineHeight: 1.5,
                color: t.fg,
              }}>{dive.deliverable}</div>
            </div>
            <div style={{ marginTop: 28, display: 'flex', gap: 32 }}>
              {dive.stats.map((s) => (
                <div key={s.k}>
                  <div style={{
                    fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
                    color: t.fgMuted, textTransform: 'uppercase', marginBottom: 4,
                  }}>{s.k}</div>
                  <div style={{
                    fontFamily: 'var(--ca-display)', fontSize: 17, color: t.fg,
                  }}>{s.v}</div>
                </div>
              ))}
            </div>
          </div>
          {/* Right column — lesson list */}
          <div style={{ flex: '1 1 0', padding: '46px 48px 46px' }}>
            <div style={{
              fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
              color: t.fgMuted, textTransform: 'uppercase', marginBottom: 24,
            }}>Lessons in this module</div>
            <ol style={{
              margin: 0, padding: 0, listStyle: 'none',
              display: 'flex', flexDirection: 'column', gap: 0,
            }}>
              {dive.lessons.map((l, i) => (
                <li key={i} style={{
                  display: 'flex', gap: 18, alignItems: 'baseline',
                  padding: '14px 0', borderBottom: i < dive.lessons.length - 1 ? `1px solid ${t.line}` : 'none',
                }}>
                  <span style={{
                    fontFamily: 'var(--ca-mono)', fontSize: 11, color: t.fgMuted,
                    flex: '0 0 28px', letterSpacing: '0.05em',
                  }}>{String(i + 1).padStart(2, '0')}</span>
                  <span style={{
                    fontFamily: 'var(--ca-display)', fontSize: 16,
                    color: t.fg, letterSpacing: '-0.005em', lineHeight: 1.4,
                  }}>{l}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
}

function LearningOutcomes({ t }) {
  const left = OUTCOMES.slice(0, 5);
  const right = OUTCOMES.slice(5);
  return (
    <section style={{ padding: '120px 56px 60px' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
        color: t.fgMuted, textTransform: 'uppercase', marginBottom: 24,
      }}>
        <span style={{ width: 22, height: 1, background: t.fgMuted }} />
        Learning outcomes
      </div>
      <div style={{ display: 'flex', gap: 60, alignItems: 'flex-end' }}>
        <h2 style={{
          margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
          fontSize: 56, lineHeight: 1.02, letterSpacing: '-0.035em', color: t.fg,
          maxWidth: 760, flex: 1, textWrap: 'balance',
        }}>On completion of the programme, students will be able to&hellip;</h2>
        <div style={{
          flex: '0 0 300px', paddingBottom: 10,
          fontFamily: 'var(--ca-display)', fontSize: 14.5, lineHeight: 1.55,
          color: t.fgSoft,
        }}>Outcomes map one-to-one onto the ten modules of the programme. Each is assessed through a written deliverable and a brief oral defence in the cohort review.</div>
      </div>
      <div style={{
        marginTop: 56,
        display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 56,
        borderTop: `1px solid ${t.line}`,
      }}>
        {[left, right].map((col, ci) => (
          <ol key={ci} start={ci * 5 + 1} style={{
            margin: 0, padding: 0, listStyle: 'none',
          }}>
            {col.map((o, i) => (
              <li key={i} style={{
                display: 'flex', gap: 22, alignItems: 'baseline',
                padding: '20px 0', borderBottom: `1px solid ${t.line}`,
              }}>
                <span style={{
                  fontFamily: 'var(--ca-mono)', fontSize: 11, color: t.fgMuted,
                  flex: '0 0 28px', letterSpacing: '0.05em',
                }}>{String(ci * 5 + i + 1).padStart(2, '0')}</span>
                <span style={{
                  fontFamily: 'var(--ca-display)', fontSize: 17,
                  color: t.fg, letterSpacing: '-0.005em', lineHeight: 1.4,
                }}>{o}</span>
              </li>
            ))}
          </ol>
        ))}
      </div>
      <div style={{
        marginTop: 36, display: 'flex',
        border: `1px solid ${t.line}`, borderRadius: 14,
        background: t.bgPanel,
      }}>
        <div style={{
          padding: '20px 26px',
          borderRight: `1px solid ${t.line}`,
          display: 'flex', alignItems: 'center', gap: 10,
          fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.18em',
          color: t.accent, textTransform: 'uppercase',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: 999, background: t.accent, boxShadow: `0 0 6px ${t.accent}` }} />
          Assessment
        </div>
        {ASSESSMENT.map((a, i, arr) => (
          <div key={a.k} style={{
            flex: 1, padding: '20px 26px',
            borderRight: i < arr.length - 1 ? `1px solid ${t.line}` : 'none',
            display: 'flex', flexDirection: 'column', gap: 4,
          }}>
            <span style={{
              fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.14em',
              color: t.fgMuted, textTransform: 'uppercase',
            }}>{a.k}</span>
            <span style={{
              fontFamily: 'var(--ca-display)', fontSize: 15, color: t.fg,
              letterSpacing: '-0.005em',
            }}>{a.v}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function FormatSection({ t, c }) {
  return (
    <section style={{ padding: '120px 56px 60px' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
        color: t.fgMuted, textTransform: 'uppercase', marginBottom: 24,
      }}>
        <span style={{ width: 22, height: 1, background: t.fgMuted }} />
        {c.formatKicker}
      </div>
      <h2 style={{
        margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
        fontSize: 56, lineHeight: 1.02, letterSpacing: '-0.035em', color: t.fg,
        maxWidth: 800, marginBottom: 56,
      }}>{c.formatTitle}</h2>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0,
        borderTop: `1px solid ${t.line}`, borderLeft: `1px solid ${t.line}`,
      }}>
        {FORMAT.map((f, i) => (
          <div key={f.label} style={{
            padding: '32px 32px 36px',
            borderRight: `1px solid ${t.line}`, borderBottom: `1px solid ${t.line}`,
            minHeight: 180,
          }}>
            <div style={{
              fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
              color: t.fgMuted, textTransform: 'uppercase', marginBottom: 14,
            }}>{String(i + 1).padStart(2, '0')}</div>
            <h4 style={{
              margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
              fontSize: 22, letterSpacing: '-0.018em', color: t.fg,
              marginBottom: 10,
            }}>{f.label}</h4>
            <p style={{
              margin: 0, fontFamily: 'var(--ca-display)', fontSize: 14,
              lineHeight: 1.55, color: t.fgSoft,
            }}>{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function EnrollBand({ t, c }) {
  return (
    <section style={{ padding: '40px 56px 100px' }}>
      <div style={{
        position: 'relative', overflow: 'hidden',
        background: t.bgAlt, borderRadius: 24,
        padding: '64px 56px',
        border: `1px solid ${t.line}`,
      }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: `radial-gradient(ellipse 50% 100% at 100% 50%, ${t.accentSoft} 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />
        <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 60 }}>
          <div style={{ flex: 1, maxWidth: 720 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.16em',
              color: t.accent, textTransform: 'uppercase', marginBottom: 22,
            }}>
              <span style={{ width: 7, height: 7, borderRadius: 999, background: t.accent, boxShadow: `0 0 8px ${t.accent}` }} />
              142 / 180 seats remaining
            </div>
            <h2 style={{
              margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
              fontSize: 56, lineHeight: 1.02, letterSpacing: '-0.035em', color: t.fg,
              textWrap: 'balance', maxWidth: 720,
            }}>{c.enrollTitle}</h2>
            <p style={{
              margin: '20px 0 0', fontFamily: 'var(--ca-display)', fontSize: 16,
              lineHeight: 1.55, color: t.fgSoft, maxWidth: 540,
            }}>{c.enrollSub}</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'flex-end' }}>
            <button style={{
              background: t.accent, color: t.accentInk, border: 'none',
              padding: '16px 26px', borderRadius: 999, fontFamily: 'var(--ca-display)',
              fontSize: 16, fontWeight: 500, letterSpacing: '-0.005em', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              {c.cta}
              <span style={{ fontSize: 18, lineHeight: 1 }}>→</span>
            </button>
            <button style={{
              background: 'transparent', color: t.fg, border: `1px solid ${t.line}`,
              padding: '15px 22px', borderRadius: 999, fontFamily: 'var(--ca-display)',
              fontSize: 14, fontWeight: 500, letterSpacing: '-0.005em', cursor: 'pointer',
            }}>{c.secCta}</button>
          </div>
        </div>
      </div>
    </section>
  );
}

function Courses({ tone = 'mix' }) {
  const t = THEMES.greenDark;
  const c = TONE[tone];
  return (
    <div style={{
      width: '100%', minHeight: '100%', background: t.bg, color: t.fg,
      fontFamily: 'var(--ca-display)', position: 'relative', overflow: 'hidden',
    }}>
      <Nav t={t} active="Courses" />
      <PageHero t={t} c={c} />

      <TrackHeader t={t} label={c.tier1Label} name={c.tier1Name} lead={c.tier1Lead} />
      <ModuleRow t={t} modules={MODULES.beginner} highlightFirst />
      <DeepDive t={t} c={c} dive={DEEP_DIVES.beginner} lead={c.deepDive1Lead} secCta={c.secCta} />

      <TrackHeader t={t} label={c.tier2Label} name={c.tier2Name} lead={c.tier2Lead} />
      <ModuleRow t={t} modules={MODULES.advanced} highlightFirst />
      <DeepDive t={t} c={c} dive={DEEP_DIVES.advanced} lead={c.deepDive2Lead} secCta={c.secCta} />

      <LearningOutcomes t={t} />
      <EnrollBand t={t} c={c} />
      <Footer t={t} />
    </div>
  );
}

window.Courses = Courses;
