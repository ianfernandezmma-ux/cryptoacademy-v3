import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { loadLatest, fmtUtc, type Latest } from "../lib/data";

const STEPS = [
  {
    n: "01",
    title: "Learn the basics",
    body: "Ten short modules take you from reading your first candle chart to managing risk like a professional. No prior experience, no coding.",
    to: "/learn",
    cta: "Start the track",
  },
  {
    n: "02",
    title: "Read the daily brief",
    body: "Every morning at 07:00 UTC we publish a plain-English overview of what happened in BTC and ETH and what to watch today. Five minutes, no noise.",
    to: "/brief",
    cta: "Read today's brief",
  },
  {
    n: "03",
    title: "Check the signal",
    body: "Our model reads the market every day and tells you which way it leans — and, crucially, when there is no clear edge. Most days there isn't. That honesty is the product.",
    to: "/today",
    cta: "See today's signal",
  },
];

export default function Home() {
  const [latest, setLatest] = useState<Latest | null | undefined>(undefined);
  useEffect(() => {
    loadLatest().then(setLatest);
  }, []);

  return (
    <>
      {/* hero */}
      <section className="ca-hero">
        <div className="ca-hero-bg" />
        <div className="ca-hero-dots" />
        <div className="ca-container ca-hero-grid">
          <div>
            <span className="ca-chip">
              <span className="ca-dot" />
              BTC · ETH · Updated daily
            </span>
            <h1 className="ca-h1" style={{ marginTop: 22 }}>
              Learn the market.
              <br />
              Use the signal.
            </h1>
            <p className="ca-lead">
              CryptoAcademy teaches you how Bitcoin and Ethereum really move — and hands
              you the same daily model signal and market brief we use ourselves. Built
              for people starting out, honest about uncertainty.
            </p>
            <div style={{ display: "flex", gap: 12, marginTop: 28, flexWrap: "wrap" }}>
              <Link to="/today" className="ca-btn ca-btn-primary">
                Today's signal <span aria-hidden>→</span>
              </Link>
              <Link to="/learn" className="ca-btn ca-btn-ghost">
                Start learning
              </Link>
            </div>
          </div>
          <div className="ca-hero-coin">
            <img src={`${import.meta.env.BASE_URL}assets/coin.png`} alt="" />
          </div>
        </div>
      </section>

      {/* live status band */}
      <div className="ca-container">
        <div className="ca-band" style={{ borderRadius: 14, overflow: "hidden" }}>
          <div className="ca-band-cell">
            <span className="ca-mono-label">Signal status</span>
            <b>
              {latest === undefined
                ? "…"
                : latest === null
                  ? "Pending"
                  : latest.signals.some((s) => s.meta_gate?.pass)
                    ? "Active signal today"
                    : "No trade today"}
            </b>
          </div>
          <div className="ca-band-cell">
            <span className="ca-mono-label">Last updated</span>
            <b>{latest ? fmtUtc(latest.generated_at) : "—"}</b>
          </div>
          <div className="ca-band-cell">
            <span className="ca-mono-label">Markets covered</span>
            <b>Bitcoin · Ethereum</b>
          </div>
          <div className="ca-band-cell">
            <span className="ca-mono-label">Daily brief</span>
            <b>07:00 UTC</b>
          </div>
        </div>
      </div>

      {/* how you use it */}
      <section className="ca-section">
        <div className="ca-container">
          <div className="ca-section-head">
            <div className="ca-kicker">How you use it</div>
            <h2 className="ca-h2">Three habits. A few minutes a day.</h2>
          </div>
          <div className="ca-signal-grid">
            {STEPS.map((s) => (
              <Link
                key={s.n}
                to={s.to}
                className="ca-panel ca-panel-pad ca-card-hover"
                style={{ textDecoration: "none", display: "flex", flexDirection: "column", gap: 12 }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span className="ca-mono-label">Step / {s.n}</span>
                  <span
                    style={{
                      fontSize: 44,
                      fontWeight: 400,
                      color: s.n === "01" ? "var(--accent)" : "var(--fg-dim)",
                      letterSpacing: "-0.04em",
                      lineHeight: 0.9,
                    }}
                  >
                    {s.n}
                  </span>
                </div>
                <h3 style={{ margin: 0, fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em" }}>
                  {s.title}
                </h3>
                <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.55, color: "var(--fg-soft)", flex: 1 }}>
                  {s.body}
                </p>
                <span style={{ color: "var(--accent)", fontSize: 14, fontWeight: 500 }}>
                  {s.cta} →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* honesty note */}
      <section className="ca-section">
        <div className="ca-container">
          <div className="ca-notice">
            <span className="ca-dot" />
            <span>
              <b style={{ color: "var(--fg)" }}>Why trust this?</b> Every signal is
              published with a timestamp <i>before</i> the market resolves it, and we
              show you the misses along with the hits. When our model has no edge, the
              site says so — “no signal” is a result, not a failure.
            </span>
          </div>
        </div>
      </section>
    </>
  );
}
