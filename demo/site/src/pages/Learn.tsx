// Learn track — curriculum migrated from the legacy demo (courses.jsx MODULES),
// de-faked: no invented cohort seats, no enroll theater. Lessons ship progressively.

type Module = {
  n: string;
  title: string;
  summary: string;
  takeaway: string;
  status: "available" | "soon";
};

const BEGINNER: Module[] = [
  {
    n: "B·01",
    title: "Reading the Chart",
    summary: "Candles, time frames, and basic price action.",
    takeaway: "Read any candle chart without feeling lost.",
    status: "soon",
  },
  {
    n: "B·02",
    title: "Trend & Structure",
    summary: "Swing points, higher highs and lower lows, market structure.",
    takeaway: "Tell an uptrend from chop in five seconds.",
    status: "soon",
  },
  {
    n: "B·03",
    title: "Support & Resistance",
    summary: "Levels, supply and demand zones, and how price reacts.",
    takeaway: "Draw the handful of levels that actually matter.",
    status: "soon",
  },
  {
    n: "B·04",
    title: "Core Indicators",
    summary: "Moving averages, RSI, and MACD without the noise.",
    takeaway: "Use three indicators well instead of thirty badly.",
    status: "soon",
  },
  {
    n: "B·05",
    title: "Risk & Position Sizing",
    summary: "Stops, R-multiples, and the trading journal.",
    takeaway: "Survive being wrong — the only non-negotiable skill.",
    status: "soon",
  },
];

const ADVANCED: Module[] = [
  {
    n: "A·01",
    title: "Market Phases & Wyckoff",
    summary: "Accumulation, distribution, springs and upthrusts.",
    takeaway: "See which phase the market is in before picking a side.",
    status: "soon",
  },
  {
    n: "A·02",
    title: "Volume Profile & Order Flow",
    summary: "VPVR, footprint, delta, and absorption.",
    takeaway: "Read where the real business is being done.",
    status: "soon",
  },
  {
    n: "A·03",
    title: "Liquidity & Smart Money",
    summary: "Order blocks, fair value gaps, and liquidity sweeps.",
    takeaway: "Understand the moves designed to shake you out.",
    status: "soon",
  },
  {
    n: "A·04",
    title: "Multi-Timeframe Confluence",
    summary: "Top-down analysis, alignment, and entry timing.",
    takeaway: "Stack timeframes so your entries stop fighting the tide.",
    status: "soon",
  },
  {
    n: "A·05",
    title: "Building Your Edge",
    summary: "Systemising setups, expectancy, drawdown discipline.",
    takeaway: "Turn scattered trades into a repeatable process.",
    status: "soon",
  },
];

function ModuleCard({ m }: { m: Module }) {
  return (
    <div className="ca-panel ca-module-card ca-card-hover">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="ca-mono-label">{m.n}</span>
        <span className="ca-chip" style={{ padding: "4px 10px", fontSize: 9 }}>
          <span className={`ca-dot ${m.status === "available" ? "" : "ca-dot--muted"}`} />
          {m.status === "available" ? "Available" : "Coming soon"}
        </span>
      </div>
      <h3>{m.title}</h3>
      <p>{m.summary}</p>
      <div className="ca-module-foot">
        <span className="ca-mono-label" style={{ letterSpacing: "0.06em", textTransform: "none" }}>
          You'll be able to: {m.takeaway}
        </span>
      </div>
    </div>
  );
}

export default function Learn() {
  return (
    <div className="ca-container">
      <section className="ca-section" style={{ paddingTop: "clamp(32px, 5vw, 56px)" }}>
        <div className="ca-kicker">Learn</div>
        <h1 className="ca-h1">From first candle to real discipline.</h1>
        <p className="ca-lead">
          Ten modules in two tracks. Everything is built around BTC and ETH — the two
          markets our signal covers — so what you learn each week is what you practice
          each morning with the brief and the signal.
        </p>
      </section>

      <section className="ca-section">
        <div className="ca-section-head">
          <div className="ca-kicker">Track one</div>
          <h2 className="ca-h2">Foundations.</h2>
          <p className="ca-lead" style={{ fontSize: 15 }}>
            Start here even if you've traded before. B·05 — risk — is the module that
            pays for all the others.
          </p>
        </div>
        <div className="ca-module-grid">
          {BEGINNER.map((m) => (
            <ModuleCard key={m.n} m={m} />
          ))}
        </div>
      </section>

      <section className="ca-section">
        <div className="ca-section-head">
          <div className="ca-kicker">Track two</div>
          <h2 className="ca-h2">Advanced reading.</h2>
          <p className="ca-lead" style={{ fontSize: 15 }}>
            How professionals read intent behind price. Unlocks after Foundations.
          </p>
        </div>
        <div className="ca-module-grid">
          {ADVANCED.map((m) => (
            <ModuleCard key={m.n} m={m} />
          ))}
        </div>
      </section>

      <section className="ca-section">
        <div className="ca-notice">
          <span className="ca-dot ca-dot--warn" />
          <span>
            <b style={{ color: "var(--fg)" }}>Lessons are being produced.</b> Module
            content ships progressively — the daily brief and signal already work as
            your practice ground from day one.
          </span>
        </div>
      </section>
    </div>
  );
}
