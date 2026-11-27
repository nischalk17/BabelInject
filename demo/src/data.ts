/** Types of the exported JSON (see src/aie/analysis/demo_export.py) and the loader. */

export interface Stat {
  k: number;
  n: number;
  rate: number;
  lo: number;
  hi: number;
}

export interface Cell {
  model_tag: string;
  defense: string;
  attack: string;
  language: string;
  channel: string;
  asr: Stat;
  attacked_utility?: Stat | null;
  item_opened?: Stat | null;
  attack_attempted?: Stat | null;
}

export interface CountRow extends Stat {
  model_tag: string;
  defense: string;
  language: string;
  channel: string;
  metric: string;
}

export interface Effect {
  model_tag: string;
  defense: string;
  language: string;
  channels: string;
  asr_k: number;
  asr_n: number;
  base_asr_k: number;
  base_asr_n: number;
  reduction_pp: number;
  reduction_lo_pp: number;
  reduction_hi_pp: number;
  utility_k: number;
  utility_n: number;
  base_utility_k: number;
  base_utility_n: number;
  utility_change_pp: number;
  utility_change_lo_pp: number;
  utility_change_hi_pp: number;
}

export interface PairedRow {
  model_tag: string;
  defense: string;
  language: string;
  channels: string;
  attacks: string;
  n: number;
  k: number;
  base_k: number;
  rate: number;
  lo: number;
  hi: number;
  base_rate: number;
  base_lo: number;
  base_hi: number;
  reduction_pp: number;
  reduction_lo_pp: number;
  reduction_hi_pp: number;
}

export interface BenignRow {
  model_tag: string;
  defense: string;
  utility: Stat;
}

export interface Study {
  id: string;
  title: string;
  status: "ok" | "not_run";
  cells: Cell[];
  benign: BenignRow[];
  effects: Effect[];
  paired: PairedRow[];
  pooled: CountRow[];
  metrics: Record<string, CountRow[]>;
}

export interface Summary {
  schema_version: number;
  studies: Study[];
}

export interface ModelInfo {
  tag: string;
  provider: string;
  rows_read: number;
  first_run: string | null;
  last_run: string | null;
}

export interface Meta {
  schema_version: number;
  git_commit: string;
  repo_url: string;
  report_url: string;
  models: ModelInfo[];
  scenarios_by_study: Record<string, number>;
}

export interface Data {
  summary: Summary;
  meta: Meta;
}

async function fetchJson<T>(name: string): Promise<T> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${name}`);
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  return (await response.json()) as T;
}

export async function loadData(): Promise<Data> {
  const [summary, meta] = await Promise.all([
    fetchJson<Summary>("summary.json"),
    fetchJson<Meta>("meta.json"),
  ]);
  return { summary, meta };
}

export function studyById(data: Data, id: string): Study | undefined {
  return data.summary.studies.find((s) => s.id === id);
}

export interface TraceIndexEntry {
  id: string;
  title: string;
  why_featured: string;
  pair_with: string | null;
  model_tag: string;
  run_date: string | null;
  defense: string;
  attack_id: string | null;
  language: string | null;
  channel: string | null;
  attack_success: boolean | null;
  utility_success: boolean;
}

export interface DefenseEvent {
  type: string;
  tool?: string;
  verdict?: boolean | null;
  reply?: string;
  to?: string;
}

export interface TraceStep {
  i: number;
  kind: "user" | "assistant" | "tool" | "final";
  text: string;
  tool_calls?: { name: string; args: Record<string, unknown> }[];
  tool?: { name: string; args: Record<string, unknown>; ok: boolean | null };
  events?: DefenseEvent[];
  injection_spans: number[][];
}

export interface UtilityCheck {
  type: string;
  text: string;
  passed: boolean;
}

export interface Trace {
  id: string;
  title: string;
  why_featured: string;
  pair_with: string | null;
  model_tag: string;
  run_date: string | null;
  config_name: string | null;
  prompt_version: string;
  defense: { name: string; version: string };
  scenario: {
    scenario_id: string;
    task_id: string;
    attack_id: string | null;
    language: string | null;
    channel: string | null;
  };
  task_prompt: string;
  system_prompt: string;
  injection: {
    attack_id: string;
    language: string;
    channel: string;
    payload: string;
    located: boolean;
    note: string | null;
  } | null;
  steps: TraceStep[];
  stop_reason: string;
  outbox: { to: string[]; subject: string; body: string }[];
  verdict: {
    attack_success: boolean | null;
    utility_success: boolean;
    failed_utility_checks: string[];
    rule: {
      id: string;
      text: string;
      matched_email: { to: string[]; subject: string; body: string } | null;
      blocked_attempts: { args: Record<string, unknown>; result: string }[];
    } | null;
    utility_checks: UtilityCheck[];
  };
}

export async function loadTraceIndex(): Promise<TraceIndexEntry[]> {
  const index = await fetchJson<{ traces: TraceIndexEntry[] }>("traces/index.json");
  return index.traces;
}

export async function loadTrace(id: string): Promise<Trace> {
  return fetchJson<Trace>(`traces/${encodeURIComponent(id)}.json`);
}
