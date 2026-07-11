import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { loadLatest, fmtUtc, type Latest } from "../lib/data";
import Ambient from "../components/Ambient";

const BASE = import.meta.env.BASE_URL;

const STEPS = [
  {
    n: "01",
    title: "Learn the basics",
    body: "Ten short modules take you from reading your first candle chart to managing risk like a professional. No prior experience, no coding.",
    to: "/learn",
    cta: "Start the track",
    cover: `${BASE}assets/terrain.webp`,
    alt: "Dark terrain model traced by neon-green contour lines",
  },
  {
    n: "02",
    title: "Read the daily brief",
    body: "Every morning at 07:00 UTC we publish a plain-English overview of what happened in BTC and ETH and what to watch today. Five minutes, no noise.",
    to: "/brief",
    cta: "Read today's brief",
    cover: `${BASE}assets/desk.webp`,
    alt: "Dark desk at dawn with a notebook and a small glowing green lamp",
  },
  {
    n: "03",
    title: "Check the signal",
    body: "Our model reads the market every day and tells you which way it leans — and, crucially, when there is no clear edge. Most days there isn't. That honesty is the product.",
    to: "/today",
    cta: "See today's signal",
    cover: `${BASE}assets/observatory.webp`,
    alt: "Radio telescope at night under a thin green scan line",
  },
];

export default function Home() {
  const [latest, setLatest] = useState<Latest | null | undefined>(undefined);
  const coinRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    loadLatest().then(setLatest);
  }, []);

  // Autoplay reliably: React doesn't reflect `muted` into the DOM attribute,
  // and StrictMode's double-mount can interrupt a mount-time play() — so we
  // (re)try after mount and again once the video has data.
  useEffect(() => {
    const v = coinRef.current;
    if (!v) return;
    v.muted = true;
    const tryPlay = () => v.play().catch(() => {});
    tryPlay();
    v.addEventListener("canplay", tryPlay);
    return () => v.removeEventListener("canplay", tryPlay);
  }, []);

  return (
    <>
      {/* hero */}
      <section className="ca-hero ca-ambient">
        <div className="ca-hero-bg" />
        <Ambient name="ambient-stage" opacity={0.55} />
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
            <video
              ref={coinRef}
              autoPlay
              muted
              loop
              playsInline
              poster={`${BASE}assets/coin-hero.webp`}
              aria-hidden
            >
              <source src={`${BASE}assets/coin-hero.mp4`} type="video/mp4" />
            </video>
            <video
              className="ca-hero-coin-eth"
              autoPlay
              muted
              loop
              playsInline
              poster={`${BASE}assets/eth-dark-loop-poster.webp`}
              aria-hidden
            >
              <source src={`${BASE}assets/eth-dark-loop.mp4`} type="video/mp4" />
            </video>
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
                <img className="ca-cover" src={s.cover} alt={s.alt} loading="lazy" />
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
          <div
            className="ca-panel ca-panel-pad"
            style={{ display: "flex", gap: 22, alignItems: "center", flexWrap: "wrap" }}
          >
            <video
              className="ca-seal-video"
              autoPlay
              muted
              loop
              playsInline
              poster={`${BASE}assets/seal-loop-poster.webp`}
              aria-hidden
            >
              <source src={`${BASE}assets/seal-loop.mp4`} type="video/mp4" />
            </video>
            <div style={{ flex: 1, minWidth: 260 }}>
              <div className="ca-kicker">Sealed before the outcome</div>
              <p style={{ margin: "10px 0 0", fontSize: 14.5, lineHeight: 1.6, color: "var(--fg-soft)" }}>
                <b style={{ color: "var(--fg)" }}>Why trust this?</b> Every signal is
                published with a timestamp <i>before</i> the market resolves it, and we
                show you the misses along with the hits. When our model has no edge, the
                site says so — “no signal” is a result, not a failure.
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
