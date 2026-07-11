import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  loadBrief,
  loadBriefsIndex,
  fmtDateLong,
  fmtUtc,
  type Brief,
  type BriefsIndex,
} from "../lib/data";
import Pending from "../components/Pending";
import Ambient from "../components/Ambient";

export default function BriefPage() {
  const { date } = useParams<{ date?: string }>();
  const [index, setIndex] = useState<BriefsIndex | null | undefined>(undefined);
  const [brief, setBrief] = useState<Brief | null | undefined>(undefined);

  useEffect(() => {
    loadBriefsIndex().then(setIndex);
  }, []);

  useEffect(() => {
    setBrief(undefined);
    if (index === undefined) return;
    const target = date ?? index?.dates?.[0];
    if (!target) {
      setBrief(null);
      return;
    }
    loadBrief(target).then(setBrief);
  }, [index, date]);

  const isToday = !date || date === index?.dates?.[0];

  return (
    <div className="ca-container">
      <section
        className="ca-section ca-ambient ca-bleed"
        style={{ padding: "clamp(48px, 7vw, 88px) 0 clamp(40px, 6vw, 72px)" }}
      >
        <Ambient name="ambient-dust" opacity={0.5} />
        <div className="ca-container ca-ambient-content">
        <div className="ca-kicker">Daily brief</div>
        <h1 className="ca-h1">
          {isToday ? "Your morning market brief." : brief ? fmtDateLong(brief.date) : "Archive"}
        </h1>
        <p className="ca-lead">
          What moved, what matters, and what to watch — for Bitcoin and Ethereum, in
          plain English, every morning at 07:00 UTC. Read it before you look at a chart.
        </p>
        <div className="ca-mast">
          <img
            src={`${import.meta.env.BASE_URL}assets/desk.webp`}
            alt="Dark desk at dawn: a closed notebook beside a small glowing green indicator lamp"
            loading="lazy"
          />
          <div className="ca-mast-inner">
            <span className="ca-mono-label" style={{ color: "var(--fg-soft)" }}>
              Written every morning by our local AI · reviewed by no one — a machine
              artifact, honestly labeled
            </span>
          </div>
        </div>
        </div>
      </section>

      {brief === undefined ? null : brief === null ? (
        <section className="ca-section">
          <Pending title="No brief published yet">
            The first brief appears here as soon as the daily pipeline goes live. In the
            meantime, the <Link to="/learn" style={{ color: "var(--accent)" }}>Learn track</Link>{" "}
            is the best place to start.
          </Pending>
        </section>
      ) : (
        <>
          {brief._fixture && (
            <div className="ca-notice" style={{ marginTop: 8 }}>
              <span className="ca-dot ca-dot--warn" />
              <span>
                <b style={{ color: "var(--fg)" }}>Sample brief.</b> This shows the daily
                format with example content — the live feed is being wired up.
              </span>
            </div>
          )}

          <section style={{ paddingTop: 28 }}>
            <article className="ca-panel" style={{ borderRadius: "var(--radius-lg)" }}>
              {/* document header */}
              <header
                style={{
                  padding: "clamp(22px, 3vw, 34px)",
                  borderBottom: "1px solid var(--line)",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <div>
                  <div className="ca-mono-label">{fmtDateLong(brief.date)}</div>
                  <div style={{ marginTop: 8, fontSize: 26, fontWeight: 500, letterSpacing: "-0.02em" }}>
                    Daily Brief — BTC &amp; ETH
                  </div>
                </div>
                <span className="ca-chip">
                  <span className="ca-dot" />
                  Published {fmtUtc(brief.generated_at)}
                </span>
              </header>

              {/* sections */}
              <div style={{ padding: "clamp(10px, 2vw, 20px) clamp(22px, 3vw, 34px)" }}>
                {brief.sections.map((s, i) => (
                  <section key={s.id} className="ca-brief-section">
                    <h3>
                      <span className="ca-num">{String(i + 1).padStart(2, "0")}</span>
                      {s.title_en}
                    </h3>
                    <p>{s.body_en}</p>
                  </section>
                ))}
              </div>
            </article>
          </section>
        </>
      )}

      {/* archive */}
      {index && index.dates.length > 0 && (
        <section className="ca-section">
          <div className="ca-section-head">
            <div className="ca-kicker">Archive</div>
            <h2 className="ca-h2">Previous briefs.</h2>
          </div>
          <div className="ca-archive-grid">
            {index.dates.map((d) => {
              const active = d === (date ?? index.dates[0]);
              return (
                <Link
                  key={d}
                  to={`/brief/${d}`}
                  className="ca-panel ca-card-hover"
                  style={{
                    padding: "18px 18px 16px",
                    textDecoration: "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    borderColor: active ? "color-mix(in srgb, var(--accent) 50%, transparent)" : undefined,
                  }}
                >
                  <span className="ca-mono-label">
                    {new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", {
                      weekday: "short",
                      timeZone: "UTC",
                    })}
                  </span>
                  <span style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.03em" }}>
                    {d.slice(8)}
                  </span>
                  <span className="ca-mono-label">
                    {new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", {
                      month: "long",
                      year: "numeric",
                      timeZone: "UTC",
                    })}
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
