import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { loadLatest, fmtUtc, type Latest } from "../lib/data";
import SignalCard from "../components/SignalCard";
import Pending from "../components/Pending";

export default function Today() {
  const [latest, setLatest] = useState<Latest | null | undefined>(undefined);
  useEffect(() => {
    loadLatest().then(setLatest);
  }, []);

  return (
    <div className="ca-container">
      <section className="ca-section" style={{ paddingTop: "clamp(32px, 5vw, 56px)" }}>
        <div className="ca-kicker">Today's signal</div>
        <h1 className="ca-h1">Which way is the market leaning?</h1>
        <p className="ca-lead">
          Once a day, our model reads price action, funding, volatility, on-chain flows
          and news, and produces one simple answer per market. A quality filter decides
          whether the read is strong enough to be a signal — most days it isn't, and we
          tell you that too.
        </p>
      </section>

      {latest === undefined ? null : latest === null ? (
        <section className="ca-section">
          <Pending title="Signal feed connecting">
            Today's signal hasn't been published yet. Signals are refreshed every
            morning at 07:00 UTC — check back shortly, or read the{" "}
            <Link to="/brief" style={{ color: "var(--accent)" }}>
              daily brief
            </Link>{" "}
            meanwhile.
          </Pending>
        </section>
      ) : (
        <>
          {latest._fixture && (
            <div className="ca-notice" style={{ marginTop: 8, marginBottom: 4 }}>
              <span className="ca-dot ca-dot--warn" />
              <span>
                <b style={{ color: "var(--fg)" }}>Sample data.</b> The live model
                connection is being wired up — these cards show the exact format with
                example values, not a real market read.
              </span>
            </div>
          )}

          <section style={{ paddingTop: 24 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 16,
                flexWrap: "wrap",
                gap: 10,
              }}
            >
              <span className="ca-mono-label">
                Updated {fmtUtc(latest.generated_at)}
              </span>
              <span className="ca-chip">
                <span className="ca-dot" />
                Next update · tomorrow 07:00 UTC
              </span>
            </div>
            <div className="ca-signal-grid">
              {latest.signals
                .filter((s) => s.horizon_h === 96)
                .map((s) => (
                  <SignalCard key={`${s.asset}-${s.horizon_h}`} s={s} />
                ))}
            </div>
          </section>

          {/* short-term reads, informational */}
          {latest.signals.some((s) => s.horizon_h === 24) && (
            <section className="ca-section">
              <div className="ca-section-head">
                <div className="ca-kicker">Short-term read</div>
                <h2 className="ca-h2">Next 24 hours — informational only.</h2>
                <p className="ca-lead" style={{ fontSize: 15 }}>
                  Over a single day the market is mostly noise, so we don't attach a
                  trade filter here. Use it for context, not decisions.
                </p>
              </div>
              <div className="ca-signal-grid">
                {latest.signals
                  .filter((s) => s.horizon_h === 24)
                  .map((s) => (
                    <SignalCard key={`${s.asset}-${s.horizon_h}`} s={s} />
                  ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* how to use */}
      <section className="ca-section">
        <div className="ca-section-head">
          <div className="ca-kicker">Using the signal well</div>
          <h2 className="ca-h2">Three rules before you act on anything.</h2>
        </div>
        <div className="ca-signal-grid">
          {[
            [
              "No signal means no trade",
              "When the filter doesn't clear a signal, the disciplined move is to do nothing. Overtrading quiet days is the #1 beginner mistake.",
            ],
            [
              "Size small, always",
              "Even an active signal is a probability, not a promise. Risk only a small, fixed fraction per idea — Module B·05 shows you exactly how.",
            ],
            [
              "Confirm with your own eyes",
              "Open the chart and check the signal against what you learned: trend, levels, structure. If your read disagrees, stand aside.",
            ],
          ].map(([title, body]) => (
            <div key={title} className="ca-panel ca-panel-pad">
              <h3 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 500, letterSpacing: "-0.015em" }}>
                {title}
              </h3>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: "var(--fg-soft)" }}>{body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
