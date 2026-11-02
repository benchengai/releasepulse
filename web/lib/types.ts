// Shape of the JSON written by `releasepulse web-export` (see releasepulse/cli.py).

export type Rate = { count: number; n: number; rate: number; low: number; high: number };

export type Release = {
  version: string;
  date: string;
  notes: string;
  items: number;
  volume: number;
  duplicates: number;
  assigned_by_date: number;
};

export type Quote = {
  item_id: string;
  release: string;
  date: string;
  source: string;
  polarity: string;
  quote: string;
  cues: string[];
};

export type SeriesPoint = {
  release: string;
  volume: number;
  complaints: Rate;
  praise: Rate;
  requests: Rate;
};

export type Feature = {
  id: string;
  name: string;
  mentions: number;
  labels: Record<string, number>;
  series: SeriesPoint[];
  quotes: Record<string, { complaints: Quote[]; praise: Quote[]; requests: Quote[] }>;
};

export type Flag = {
  kind: "regression" | "improvement";
  feature: string;
  release: string;
  previous: string;
  count: number;
  volume?: number;
  previous_count: number;
  previous_volume?: number;
  rate?: number;
  previous_rate?: number;
  diff?: number;
  low?: number;
  high?: number;
};

export type PriorityRow = {
  feature: string;
  name: string;
  complaints: Rate;
  latest: Rate;
  praise: Rate;
  requests: number;
  raw_complaint_posts: number;
  change: null | {
    baseline: string;
    baseline_rate: number;
    baseline_count: number;
    baseline_volume: number;
    diff: number;
    low: number;
    high: number;
    significant: boolean;
  };
  flags: Flag[];
  status: "regression" | "improved" | "thin evidence" | "ongoing";
  since: string | null;
  rank: number;
  band: number;
  raw_rank: number;
  evidence: Quote[];
  praise_evidence: Quote[];
  request_evidence: Quote[];
};

export type PriorityTable = {
  k: number;
  window: string[];
  baseline: string | null;
  volume: number;
  latest: string;
  latest_volume: number;
  rows: PriorityRow[];
};

export type Requirement = {
  id: string;
  type: string;
  statement: string;
  rationale: string;
  acceptance: string[];
  stakeholder: string;
  status: string;
  evidence: { meeting: string; segment_id: string; speaker: string; quote: string; date: string }[];
  quality: { kind: string; detail: string }[];
  uncertainty: { flag: boolean; label: string | null; cues: { kind: string; detail: string }[] };
  releasepulse: { feature: string; feature_name: string; rank: number; band: number; status: string; since: string | null };
};

export type Item = {
  date: string;
  version: string;
  source: string;
  rating: number | null;
  release: string | null;
  assigned_by: string;
  duplicate_of: string | null;
  text: string;
};

export type EvalSummary = {
  role: string;
  runs_per_model: number;
  models: Record<string, Record<string, { mean: number; min: number; max: number }>>;
};

export type Analysis = {
  notice: string | null;
  app: { id: string; name: string; product?: string; description?: string };
  generated: string;
  model: string;
  embedding_model: string;
  settings: { cluster_threshold: number; min_count: number; raw_min_increase: number; raw_min_ratio: number };
  releases: Release[];
  items: Record<string, Item>;
  features: Feature[];
  flags: Flag[];
  flags_without_dedupe: Flag[];
  raw_flags: Flag[];
  priority: { default: number; tables: Record<string, PriorityTable> };
  requirements: null | { requirements: Requirement[] };
  extraction: { items_sent: number; aspects: number; rejected: number; missing_items: string[]; quote_validity: number | null };
  llm: { calls: number; cost_usd: number | null; wall_s: number | null; input_tokens: number; output_tokens: number };
  evaluation?: EvalSummary;
};

export const pct = (x: number, digits = 0) => `${(100 * x).toFixed(digits)}%`;
export const pts = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(100 * x).toFixed(0)}`;
export const modelLabel = (m: string) => m.replaceAll("openai:", "").replace(">", " → ");
export const sourceLabel = (s: string) =>
  ({ app_store: "App Store review", play_store: "Play Store review", issue_tracker: "Issue ticket" })[s] ?? s;
