// ml-model.jsx — Live predictions dashboard for BTC + ETH.
// Static page. Illustrative values throughout; intended to be wired
// to a Python LightGBM backend later.

const PREDICTIONS = [
  {
    asset: 'BTC', name: 'Bitcoin', price: '67,420.18', change24h: '+2.31',
    bias: 'LONG', confidence: 72, positionSize: '1.2 × R',
    timeHorizon: '4 – 8 h', nextReview: '07:00 UTC',
    riskFlags: ['Funding rate stretched', 'Weekend liquidity reduced'],
    updatedAt: '14:23 UTC',
  },
  {
    asset: 'ETH', name: 'Ethereum', price: '3,512.40', change24h: '+1.04',
    bias: 'LONG', confidence: 64, positionSize: '0.8 × R',
    timeHorizon: '4 – 8 h', nextReview: '07:00 UTC',
    riskFlags: ['Confidence below threshold', 'Range-bound regime'],
    updatedAt: '14:23 UTC',
  },
];

const METRICS = [
  { k: 'Cumulative return',  v: 'Pending' },
  { k: 'Sharpe ratio',       v: 'Pending' },
  { k: 'Sortino ratio',      v: 'Pending' },
  { k: 'Max drawdown',       v: 'Pending' },
  { k: 'Win rate',           v: 'Pending' },
  { k: 'Profit factor',      v: 'Pending' },
];

// 8 features, illustrative ranks; replace with real importance scores
// from LightGBM `feature_importances_` once trained.
const FEATURES = [
  { name: 'RSI(14) divergence',         imp: 1.00 },
  { name: 'EMA(20) / EMA(50) state',    imp: 0.86 },
  { name: 'Volume profile · POC distance', imp: 0.74 },
  { name: 'Market structure score',     imp: 0.68 },
  { name: 'Funding rate · Z-score',  imp: 0.55 },
  { name: 'ATR / price (volatility)',   imp: 0.42 },
  { name: 'On-balance volume slope',    imp: 0.31 },
  { name: 'Liquidity pool proximity',   imp: 0.24 },
];

// ─── small atoms ────────────────────────────────────────────────────────────────
function MlSectionHead({ t, kicker, title, sub, right }) {
  return (
    <div style={{ padding: '92px 56px 50px', display: 'flex', alignItems: 'flex-end', gap: 60 }}>
      <div style={{ flex: 1 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
          color: t.fgMuted, textTransform: 'uppercase', marginBottom: 24,
        }}>
          <span style={{ width: 22, height: 1, background: t.fgMuted }} />
          {kicker}
        </div>
        <h2 style={{
          margin: 0, fontFamily: 'var(--ca-display)', fontWeight: 500,
          fontSize: 56, lineHeight: 1.02, letterSpacing: '-0.035em',
          color: t.fg, textWrap: 'balance', maxWidth: 820,
        }}>{title}</h2>
        {sub && (
          <p style={{
            margin: '20px 0 0', maxWidth: 540,
            fontFamily: 'var(--ca-display)', fontSize: 16, lineHeight: 1.55,
            color: t.fgSoft,
          }}>{sub}</p>
        )}
      </div>
      {right}
    </div>
  );
}

function AssetGlyph({ t, asset }) {
  const isBTC = asset === 'BTC';
  return (
    <div style={{
      width: 44, height: 44, borderRadius: 999,
      border: `1px solid ${t.line}`, background: t.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flex: '0 0 auto',
    }}>
      <span style={{
        fontFamily: 'var(--ca-display)', fontWeight: 500, fontSize: 22,
        color: t.fg, letterSpacing: '-0.02em',
      }}>{isBTC ? '₿' : 'Ξ'}</span>
    </div>
  );
}

function MlLabel({ t, children }) {
  return (
    <div style={{
      fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
      color: t.fgMuted, textTransform: 'uppercase', marginBottom: 10,
    }}>{children}</div>
  );
}

// ─── page hero + status bar ────────────────────────────────────────────────
function MlPageHero({ t }) {
  return (
    <section style={{ padding: '92px 56px 50px', position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse 70% 50% at 80% 30%, ${t.accentSoft} 0%, transparent 65%)`,
        pointerEvents: 'none',
      }} />
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
        color: t.fgMuted, textTransform: 'uppercase', marginBottom: 28,
        position: 'relative',
      }}>
        <span style={{ width: 22, height: 1, background: t.fgMuted }} />
        Model dashboard
      </div>
      <div style={{ display: 'flex', gap: 60, alignItems: 'flex-end', position: 'relative' }}>
        <h1 style={{
          margin: 0, flex: 1, fontFamily: 'var(--ca-display)',
          fontWeight: 500, fontSize: 88, lineHeight: 1.0,
          letterSpacing: '-0.035em', color: t.fg, textWrap: 'balance',
          maxWidth: 920,
        }}>Live predictions for BTC and ETH.</h1>
        <div style={{ flex: '0 0 380px', paddingBottom: 14 }}>
          <p style={{
            margin: 0, fontFamily: 'var(--ca-display)', fontSize: 16,
            lineHeight: 1.6, color: t.fgSoft,
          }}>The two-asset LightGBM model produces a directional bias, a confidence score, a position-size suggestion, and a list of risk flags. Outputs refresh on each new candle close.</p>
        </div>
      </div>

      {/* status band */}
      <div style={{
        marginTop: 56, display: 'flex', borderTop: `1px solid ${t.line}`,
        borderBottom: `1px solid ${t.line}`,
      }}>
        {[
          ['Model', 'LightGBM · v0.4.2'],
          ['Assets', 'BTC · ETH'],
          ['Refresh cadence', 'Per candle close'],
          ['Last update', '14:23 UTC'],
          ['Backend', 'Connection pending'],
        ].map(([k, v], i, arr) => (
          <div key={k} style={{
            flex: 1, padding: '22px 26px',
            borderRight: i < arr.length - 1 ? `1px solid ${t.line}` : 'none',
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <span style={{ fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em', color: t.fgMuted, textTransform: 'uppercase' }}>{k}</span>
            <span style={{ fontFamily: 'var(--ca-display)', fontSize: 17, color: t.fg, letterSpacing: '-0.01em' }}>{v}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── prediction card ──────────────────────────────────────────────────────────
function BiasGlyph({ t, bias }) {
  const color = bias === 'LONG' ? t.accent : bias === 'SHORT' ? '#ef6464' : t.fgSoft;
  const path = bias === 'LONG'
    ? 'M8 36 L20 24 L28 28 L40 12'
    : bias === 'SHORT'
      ? 'M8 12 L20 24 L28 20 L40 36'
      : 'M8 24 L40 24';
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ flex: '0 0 auto' }}>
      <path d={path} stroke={color} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      {bias !== 'FLAT' && (
        <circle cx={bias === 'LONG' ? 40 : 40} cy={bias === 'LONG' ? 12 : 36} r="3" fill={color} />
      )}
    </svg>
  );
}

function ConfidenceArc({ t, value }) {
  // Half-circle arc going left-to-right, filled to `value`%.
  const R = 64;
  const c = Math.PI * R; // half-circumference
  const filled = (value / 100) * c;
  return (
    <svg width="160" height="92" viewBox="0 0 160 92" fill="none">
      <path d={`M 16 80 A ${R} ${R} 0 0 1 144 80`} stroke={t.line} strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d={`M 16 80 A ${R} ${R} 0 0 1 144 80`} stroke={t.accent} strokeWidth="6" strokeLinecap="round" fill="none"
            strokeDasharray={`${filled} ${c}`} />
    </svg>
  );
}

function PredictionCard({ t, p }) {
  const biasColor = p.bias === 'LONG' ? t.accent : p.bias === 'SHORT' ? '#ef6464' : t.fgSoft;
  return (
    <div style={{
      flex: 1, border: `1px solid ${t.line}`, borderRadius: 22,
      background: t.bgPanel, padding: '36px 38px',
      display: 'flex', flexDirection: 'column', gap: 30,
      position: 'relative', overflow: 'hidden',
    }}>
      {/* corner glow */}
      <div style={{
        position: 'absolute', top: 0, right: 0, width: 240, height: 240,
        background: `radial-gradient(circle at 100% 0%, ${t.accentSoft} 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />

      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <AssetGlyph t={t} asset={p.asset} />
          <div>
            <div style={{
              fontFamily: 'var(--ca-display)', fontSize: 24, fontWeight: 500,
              color: t.fg, letterSpacing: '-0.02em', lineHeight: 1,
            }}>{p.name} <span style={{ color: t.fgMuted, fontWeight: 400 }}>/ USD</span></div>
            <div style={{
              marginTop: 6, fontFamily: 'var(--ca-mono)', fontSize: 10,
              letterSpacing: '0.14em', color: t.fgMuted, textTransform: 'uppercase',
            }}>Spot · Feed pending</div>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--ca-mono)', fontSize: 22, color: t.fg, letterSpacing: '-0.01em' }}>${p.price}</div>
          <div style={{ marginTop: 4, fontFamily: 'var(--ca-mono)', fontSize: 11, color: t.accent }}>
            {p.change24h}% · 24h
          </div>
        </div>
      </div>

      {/* main: bias + confidence */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20,
        padding: '28px 0', borderTop: `1px solid ${t.line}`, borderBottom: `1px solid ${t.line}`,
        position: 'relative',
      }}>
        <div>
          <MlLabel t={t}>Directional bias</MlLabel>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <BiasGlyph t={t} bias={p.bias} />
            <div style={{
              fontFamily: 'var(--ca-display)', fontWeight: 500, fontSize: 56,
              letterSpacing: '-0.035em', color: biasColor, lineHeight: 1,
            }}>{p.bias}</div>
          </div>
        </div>
        <div>
          <MlLabel t={t}>Confidence</MlLabel>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
            <ConfidenceArc t={t} value={p.confidence} />
            <div style={{ paddingBottom: 6 }}>
              <div style={{
                fontFamily: 'var(--ca-display)', fontWeight: 500, fontSize: 40,
                color: t.fg, letterSpacing: '-0.03em', lineHeight: 1,
              }}>{p.confidence}%</div>
              <div style={{ marginTop: 4, fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.14em', color: t.fgMuted, textTransform: 'uppercase' }}>
                {p.confidence >= 70 ? 'High' : p.confidence >= 55 ? 'Moderate' : 'Low'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, position: 'relative' }}>
        {[
          ['Position size', p.positionSize],
          ['Time horizon', p.timeHorizon],
          ['Next review', p.nextReview],
        ].map(([k, v]) => (
          <div key={k}>
            <MlLabel t={t}>{k}</MlLabel>
            <div style={{ fontFamily: 'var(--ca-display)', fontSize: 19, color: t.fg, letterSpacing: '-0.01em' }}>{v}</div>
          </div>
        ))}
      </div>

      {/* risk flags */}
      <div style={{ position: 'relative' }}>
        <MlLabel t={t}>Risk flags</MlLabel>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {p.riskFlags.map((f) => (
            <span key={f} style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '8px 14px', borderRadius: 999,
              border: `1px solid ${t.line}`, background: t.bg,
              fontFamily: 'var(--ca-display)', fontSize: 13, color: t.fgSoft,
              letterSpacing: '-0.005em',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: 999, background: '#e9a83c' }} />
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* footer */}
      <div style={{
        marginTop: 'auto', paddingTop: 22, borderTop: `1px solid ${t.line}`,
        display: 'flex', justifyContent: 'space-between',
        fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.14em',
        color: t.fgMuted, textTransform: 'uppercase',
      }}>
        <span>Updated {p.updatedAt}</span>
        <span>Output · Illustrative</span>
      </div>
    </div>
  );
}

function PredictionsSection({ t }) {
  return (
    <section>
      <MlSectionHead
        t={t}
        kicker="Live predictions"
        title="Current model output."
        sub="Each asset card reports the model’s present directional call, confidence, suggested position size, and any active risk flags. Values illustrative pending live connection to the model."
        right={(
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            padding: '10px 16px', borderRadius: 999,
            border: `1px solid ${t.line}`, background: t.bgPanel,
            fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.14em',
            color: t.fgSoft, textTransform: 'uppercase',
            marginBottom: 6,
          }}>
            <span style={{ width: 7, height: 7, borderRadius: 999, background: '#e9a83c', boxShadow: '0 0 8px #e9a83c' }} />
            Feed offline
          </div>
        )}
      />
      <div style={{ display: 'flex', gap: 18, padding: '0 56px' }}>
        {PREDICTIONS.map((p) => <PredictionCard key={p.asset} t={t} p={p} />)}
      </div>
    </section>
  );
}

// ─── performance section ──────────────────────────────────────────────────────
function EquityCurvePlaceholder({ t }) {
  // Empty chart frame with axes; deliberately no line so the user
  // can swap in a real one. Faint grid + axis labels for context.
  const W = 1100, H = 380;
  const padL = 60, padR = 30, padT = 30, padB = 40;
  const innerW = W - padL - padR, innerH = H - padT - padB;
  const yLabels = ['+30%', '+20%', '+10%', '0%', '-10%'];
  const xLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'];
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      {/* axes */}
      <line x1={padL} y1={padT} x2={padL} y2={H - padB} stroke={t.line} strokeWidth="1" />
      <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke={t.line} strokeWidth="1" />
      {/* horizontal grid */}
      {yLabels.map((lab, i) => {
        const y = padT + (innerH / (yLabels.length - 1)) * i;
        return (
          <g key={i}>
            <line x1={padL} y1={y} x2={W - padR} y2={y} stroke={t.lineSoft} strokeWidth="0.6" strokeDasharray="2 4" />
            <text x={padL - 12} y={y + 4} textAnchor="end"
                  fontFamily="JetBrains Mono, monospace" fontSize="10"
                  fill={t.fgMuted} letterSpacing="0.05em">{lab}</text>
          </g>
        );
      })}
      {/* zero baseline */}
      {(() => {
        const y = padT + (innerH / (yLabels.length - 1)) * 3;
        return <line x1={padL} y1={y} x2={W - padR} y2={y} stroke={t.fgMuted} strokeWidth="0.8" />;
      })()}
      {/* x labels */}
      {xLabels.map((lab, i) => {
        const x = padL + (innerW / (xLabels.length - 1)) * i;
        return (
          <text key={i} x={x} y={H - padB + 18} textAnchor="middle"
                fontFamily="JetBrains Mono, monospace" fontSize="10"
                fill={t.fgMuted} letterSpacing="0.05em">{lab}</text>
        );
      })}
      {/* placeholder message */}
      <g transform={`translate(${W / 2}, ${padT + innerH / 2 - 8})`}>
        <rect x={-130} y={-20} width="260" height="44" rx="22"
              fill={t.bgPanel} stroke={t.line} />
        <circle cx={-100} cy={2} r="4" fill="#e9a83c" />
        <text x={-86} y={6} textAnchor="start"
              fontFamily="JetBrains Mono, monospace" fontSize="11"
              fill={t.fgSoft} letterSpacing="0.12em">AWAITING BACKTEST OUTPUT</text>
      </g>
    </svg>
  );
}

function PerformanceSection({ t }) {
  return (
    <section>
      <MlSectionHead
        t={t}
        kicker="Performance"
        title="Backtest and live equity — to be populated."
        sub="Cumulative return, drawdown, and standard risk metrics will appear here once the model has completed its first walk-forward validation cycle."
      />
      <div style={{ padding: '0 56px' }}>
        <div style={{
          border: `1px solid ${t.line}`, borderRadius: 18,
          background: t.bgPanel, padding: 28,
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 18,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
              <span style={{
                fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.18em',
                color: t.fgMuted, textTransform: 'uppercase',
              }}>Cumulative return</span>
              <span style={{
                padding: '4px 10px', borderRadius: 4,
                border: `1px solid ${t.line}`, background: t.bg,
                fontFamily: 'var(--ca-mono)', fontSize: 9, letterSpacing: '0.16em',
                color: t.fgMuted, textTransform: 'uppercase',
              }}>BTC + ETH (50/50)</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {['1M', '3M', '6M', '1Y', 'All'].map((r) => (
                <span key={r} style={{
                  padding: '5px 10px', borderRadius: 6,
                  fontFamily: 'var(--ca-mono)', fontSize: 11,
                  color: r === '3M' ? t.fg : t.fgMuted,
                  background: r === '3M' ? t.bg : 'transparent',
                  border: r === '3M' ? `1px solid ${t.line}` : '1px solid transparent',
                }}>{r}</span>
              ))}
            </div>
          </div>
          <EquityCurvePlaceholder t={t} />
        </div>

        {/* metric tiles */}
        <div style={{
          marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)',
          gap: 0, border: `1px solid ${t.line}`, borderRadius: 14,
          background: t.bgPanel, overflow: 'hidden',
        }}>
          {METRICS.map((m, i, arr) => (
            <div key={m.k} style={{
              padding: '24px 22px',
              borderRight: i < arr.length - 1 ? `1px solid ${t.line}` : 'none',
              display: 'flex', flexDirection: 'column', gap: 8,
            }}>
              <span style={{
                fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
                color: t.fgMuted, textTransform: 'uppercase',
              }}>{m.k}</span>
              <span style={{
                fontFamily: 'var(--ca-display)', fontSize: 28, color: t.fg,
                letterSpacing: '-0.025em', lineHeight: 1,
              }}>—</span>
              <span style={{
                fontFamily: 'var(--ca-mono)', fontSize: 10,
                color: t.fgDim, letterSpacing: '0.06em',
                display: 'inline-flex', alignItems: 'center', gap: 6,
              }}>
                <span style={{ width: 5, height: 5, borderRadius: 999, background: '#e9a83c' }} />
                {m.v}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── features section ───────────────────────────────────────────────────────
function FeaturesSection({ t }) {
  return (
    <section>
      <MlSectionHead
        t={t}
        kicker="Feature importance"
        title="Top eight features driving the model."
        sub="Ranking is illustrative and refreshes with each model retrain. The full feature set is documented in the methodology appendix."
      />
      <div style={{ padding: '0 56px' }}>
        <div style={{
          border: `1px solid ${t.line}`, borderRadius: 18,
          background: t.bgPanel, overflow: 'hidden',
        }}>
          {/* table header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '60px 1fr 110px 1.2fr 110px',
            padding: '16px 24px', borderBottom: `1px solid ${t.line}`,
            fontFamily: 'var(--ca-mono)', fontSize: 10, letterSpacing: '0.16em',
            color: t.fgMuted, textTransform: 'uppercase',
          }}>
            <span>Rank</span>
            <span>Feature</span>
            <span>Score</span>
            <span>Relative importance</span>
            <span style={{ textAlign: 'right' }}>Domain</span>
          </div>
          {/* rows */}
          {FEATURES.map((f, i) => {
            const domain = ['Momentum', 'Trend', 'Volume', 'Structure', 'Derivatives', 'Volatility', 'Volume', 'Liquidity'][i];
            return (
              <div key={f.name} style={{
                display: 'grid', gridTemplateColumns: '60px 1fr 110px 1.2fr 110px',
                padding: '18px 24px', alignItems: 'center',
                borderBottom: i < FEATURES.length - 1 ? `1px solid ${t.lineSoft}` : 'none',
              }}>
                <span style={{
                  fontFamily: 'var(--ca-mono)', fontSize: 13, color: t.fgMuted,
                }}>{String(i + 1).padStart(2, '0')}</span>
                <span style={{
                  fontFamily: 'var(--ca-display)', fontSize: 16, color: t.fg,
                  letterSpacing: '-0.005em',
                }}>{f.name}</span>
                <span style={{
                  fontFamily: 'var(--ca-mono)', fontSize: 14, color: t.fg,
                  letterSpacing: '-0.005em',
                }}>{f.imp.toFixed(2)}</span>
                <div style={{
                  height: 8, borderRadius: 999, background: t.bg,
                  overflow: 'hidden', maxWidth: 320,
                }}>
                  <div style={{
                    width: `${f.imp * 100}%`, height: '100%',
                    background: t.accent,
                    boxShadow: `0 0 12px ${t.accent}`,
                  }} />
                </div>
                <span style={{
                  fontFamily: 'var(--ca-mono)', fontSize: 11, color: t.fgMuted,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  textAlign: 'right',
                }}>{domain}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── disclaimer ───────────────────────────────────────────────────────────────────
function DisclaimerSection({ t }) {
  return (
    <section style={{ padding: '110px 56px 80px' }}>
      <div style={{
        border: `1px solid ${t.line}`, borderRadius: 18,
        background: t.bgPanel, padding: '36px 40px',
        display: 'flex', gap: 40, alignItems: 'flex-start',
      }}>
        <div style={{ flex: '0 0 220px' }}>
          <div style={{
            fontFamily: 'var(--ca-mono)', fontSize: 11, letterSpacing: '0.18em',
            color: t.accent, textTransform: 'uppercase', marginBottom: 14,
            display: 'inline-flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: t.accent, boxShadow: `0 0 6px ${t.accent}` }} />
            Disclaimer
          </div>
          <h3 style={{
            margin: 0, fontFamily: 'var(--ca-display)', fontSize: 22, fontWeight: 500,
            color: t.fg, letterSpacing: '-0.018em', lineHeight: 1.15,
          }}>Not financial advice.</h3>
        </div>
        <div style={{ flex: 1 }}>
          <p style={{
            margin: 0, fontFamily: 'var(--ca-display)', fontSize: 15,
            lineHeight: 1.6, color: t.fgSoft, maxWidth: 820,
          }}>
            This dashboard is part of an academic thesis project. Outputs produced by the model are intended for educational and research purposes only and do not constitute financial advice, a recommendation, or a solicitation to trade in any asset. Past performance, where shown, is illustrative and is not indicative of future results. Predictions are generated by a LightGBM model trained on historical and live market data; outputs may be incorrect, delayed, or stale. Cryptocurrency markets are volatile and trading carries substantial risk of loss. Readers should perform their own due diligence and consider their personal circumstances before acting on any information presented here.
          </p>
        </div>
      </div>
    </section>
  );
}

// ─── page ──────────────────────────────────────────────────────────────────────────────
function MlModel() {
  const t = THEMES.greenDark;
  return (
    <div style={{
      width: '100%', minHeight: '100%', background: t.bg, color: t.fg,
      fontFamily: 'var(--ca-display)', position: 'relative', overflow: 'hidden',
    }}>
      <Nav t={t} active="ML Model" />
      <MlPageHero t={t} />
      <PredictionsSection t={t} />
      <PerformanceSection t={t} />
      <FeaturesSection t={t} />
      <DisclaimerSection t={t} />
      <Footer t={t} />
    </div>
  );
}

window.MlModel = MlModel;
