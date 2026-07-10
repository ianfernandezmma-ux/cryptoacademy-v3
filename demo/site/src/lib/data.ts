// Typed loaders for the pipeline-written JSON artifacts (demo/contracts/site-data.md).
// Every loader returns null on any failure — the UI renders a Pending state.

export type MetaGate = {
  pass: boolean;
  p_meta: number;
  coverage_pct: number;
} | null;

export type Signal = {
  asset: "BTC" | "ETH";
  horizon_h: 24 | 96;
  p_up: number;
  direction: "UP" | "DOWN";
  meta_gate: MetaGate;
  regime: "risk_on" | "risk_off" | null;
  features_asof: string;
};

export type Latest = {
  _fixture?: boolean;
  schema_version: number;
  generated_at: string;
  commit_sha: string;
  model_version: string;
  signals: Signal[];
};

export type BriefSection = {
  id: string;
  title_en: string;
  title_es?: string;
  body_en: string;
  body_es?: string;
};

export type Brief = {
  _fixture?: boolean;
  schema_version: number;
  generated_at: string;
  date: string;
  llm?: { model: string; prompt_version: string };
  sections: BriefSection[];
};

export type BriefsIndex = {
  _fixture?: boolean;
  dates: string[];
};

async function fetchJson<T>(rel: string): Promise<T | null> {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/${rel}`, {
      cache: "no-cache",
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const loadLatest = () => fetchJson<Latest>("latest.json");
export const loadBriefsIndex = () => fetchJson<BriefsIndex>("briefs-index.json");
export const loadBrief = (date: string) => fetchJson<Brief>(`report-${date}.json`);

// ── presentation helpers (plain language for beginners) ────────────────

export function horizonLabel(h: 24 | 96): string {
  return h === 96 ? "next 4 days" : "next 24 hours";
}

export function leanStrength(pUp: number): "slight" | "moderate" | "strong" {
  const d = Math.abs(pUp - 0.5);
  if (d >= 0.12) return "strong";
  if (d >= 0.05) return "moderate";
  return "slight";
}

export function fmtUtc(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return (
    d.toISOString().slice(0, 16).replace("T", " · ") + " UTC"
  );
}

export function fmtDateLong(dateIso: string): string {
  const d = new Date(dateIso + "T00:00:00Z");
  if (Number.isNaN(d.getTime())) return dateIso;
  return d.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}
