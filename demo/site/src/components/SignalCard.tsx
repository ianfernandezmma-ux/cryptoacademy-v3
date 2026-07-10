import type { Signal } from "../lib/data";
import { horizonLabel, leanStrength } from "../lib/data";

// Plain-language translation of one model output for a beginner audience.
// No jargon on the surface; the numbers live inside the explainer.

function verdict(s: Signal): {
  word: string;
  color: string;
  sub: string;
  active: boolean;
} {
  const up = s.direction === "UP";
  const dirWord = up ? "Leaning up" : "Leaning down";
  const color = up ? "var(--accent)" : "var(--down)";

  if (s.meta_gate === null) {
    // No quality filter exists at this horizon → informational only.
    return {
      word: dirWord,
      color,
      sub: "Informational only — no trade filter at this horizon.",
      active: false,
    };
  }
  if (!s.meta_gate.pass) {
    return {
      word: "No signal",
      color: "var(--fg-soft)",
      sub: `The quality filter didn't clear a trade today. The model still leans ${up ? "up" : "down"}, but not strongly enough to act on.`,
      active: false,
    };
  }
  return {
    word: dirWord,
    color,
    sub: "Active signal — the quality filter cleared today's read.",
    active: true,
  };
}

export default function SignalCard({ s }: { s: Signal }) {
  const v = verdict(s);
  const pct = Math.round(s.p_up * 100);
  const strength = leanStrength(s.p_up);
  const up = s.direction === "UP";
  const name = s.asset === "BTC" ? "Bitcoin" : "Ethereum";
  const glyph = s.asset === "BTC" ? "₿" : "Ξ";

  return (
    <article className="ca-panel ca-panel-pad ca-card-hover">
      {/* header */}
      <div className="ca-signal-head">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="ca-asset-glyph" aria-hidden>
            {glyph}
          </span>
          <div>
            <div style={{ fontSize: 20, fontWeight: 500, letterSpacing: "-0.015em" }}>
              {name}
            </div>
            <div className="ca-mono-label" style={{ marginTop: 4 }}>
              {horizonLabel(s.horizon_h)}
            </div>
          </div>
        </div>
        <span className="ca-chip">
          <span className={`ca-dot ${v.active ? "" : "ca-dot--muted"}`} />
          {v.active ? "Active" : "Watch"}
        </span>
      </div>

      {/* verdict */}
      <div className="ca-signal-verdict">
        <svg width="42" height="42" viewBox="0 0 48 48" fill="none" aria-hidden>
          <path
            d={up ? "M8 36 L20 24 L28 28 L40 12" : "M8 12 L20 24 L28 20 L40 36"}
            stroke={v.color}
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="40" cy={up ? 12 : 36} r="3" fill={v.color} />
        </svg>
        <div style={{ flex: 1 }}>
          <div className="ca-verdict-word" style={{ color: v.color }}>
            {v.word}
          </div>
          <div style={{ marginTop: 8 }}>
            <div className={`ca-meter ${up ? "" : "ca-meter--down"}`}>
              <div style={{ width: `${up ? pct : 100 - pct}%` }} />
            </div>
            <div
              className="ca-mono-label"
              style={{ marginTop: 6, display: "flex", justifyContent: "space-between" }}
            >
              <span>{strength} lean</span>
              <span>
                {up ? pct : 100 - pct}% {up ? "up" : "down"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <p style={{ margin: "0 0 18px", fontSize: 14, lineHeight: 1.55, color: "var(--fg-soft)" }}>
        {v.sub}
      </p>

      {/* beginner explainer */}
      <details className="ca-explain">
        <summary>What does this mean?</summary>
        <div>
          <p style={{ margin: "0 0 10px" }}>
            Our model estimates the chance that {name} closes higher over the{" "}
            {horizonLabel(s.horizon_h)}. Right now it reads <b>{pct}% up / {100 - pct}% down</b> —
            a {strength} lean. Anything close to 50/50 means the market could go either way.
          </p>
          {s.meta_gate !== null && (
            <p style={{ margin: "0 0 10px" }}>
              A second model — the <b>quality filter</b> — decides whether the read is
              reliable enough to act on. It only clears about{" "}
              {Math.round(s.meta_gate.coverage_pct)}% of days; on all the others,
              “no signal” <i>is</i> the signal: stay patient, don't force trades.
            </p>
          )}
          <p style={{ margin: 0 }}>
            Use this as one input among many — never as a reason on its own to buy or
            sell. New to this? Start with the{" "}
            <a href="#/learn" style={{ color: "var(--accent)" }}>
              Learn track
            </a>
            .
          </p>
        </div>
      </details>
    </article>
  );
}
