/** Formatting only. No statistic is computed in the browser; every k, n, rate and interval is read
 * from the exported JSON, which was produced by the same functions as the project's tables. */

import type { Meta, Stat } from "./data";

export const LANGUAGES = ["en", "ne", "ne_rom", "hi", "mix"] as const;

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  ne: "Nepali",
  ne_rom: "Romanized Nepali",
  hi: "Hindi",
  mix: "Code-mixed",
  ALL: "All languages",
};

export const DEFENSE_NAMES: Record<string, string> = {
  none: "No defense",
  spotlight: "Spotlighting",
  sandwich: "Sandwich reminder",
  tool_policy: "Tool policy",
  detector: "Detector",
};

export function languageName(code: string): string {
  return LANGUAGE_NAMES[code] ?? code;
}

export function defenseName(code: string): string {
  return DEFENSE_NAMES[code] ?? code;
}

/** "qwen2.5:7b" from "ollama/qwen2.5:7b@845dbda0ea48"; the full tag is always shown in captions. */
export function modelLabel(tag: string): string {
  const withoutHash = tag.split("@")[0] ?? tag;
  const slash = withoutHash.indexOf("/");
  return slash === -1 ? withoutHash : withoutHash.slice(slash + 1);
}

export function pct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function kn(s: Pick<Stat, "k" | "n">): string {
  return `${s.k}/${s.n}`;
}

/** "3/120 (2.5%, 95% CI 0.9% to 7.1%)" */
export function withInterval(s: Stat): string {
  return `${kn(s)} (${pct(s.rate)}, 95% CI ${pct(s.lo)} to ${pct(s.hi)})`;
}

export function signedPp(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(1)} pp`;
}

/** Run dates for one model tag, from meta.json. */
export function runWindow(meta: Meta, tag: string): string {
  const model = meta.models.find((m) => m.tag === tag);
  if (!model || !model.first_run) return "run date not recorded";
  return model.first_run === model.last_run
    ? `run ${model.first_run}`
    : `runs ${model.first_run} to ${model.last_run ?? model.first_run}`;
}

/** "ollama/qwen2.5:7b@845dbda0ea48, run 2026-11-22 to 2026-11-23" for each tag. */
export function provenance(meta: Meta, tags: readonly string[]): string {
  return tags.map((tag) => `${tag}, ${runWindow(meta, tag)}`).join(" | ");
}

export const ATTACK_NAMES: Record<string, string> = {
  ALL: "All attacks pooled",
  inject_override: "Blunt override",
  inject_owner_note: "Owner note (authority)",
  inject_cc_request: "Casual request",
  inject_owner_note_plain: "Owner note, plain address",
};

export function attackName(id: string): string {
  return ATTACK_NAMES[id] ?? id;
}

export const CHANNEL_NAMES: Record<string, string> = {
  email: "Email",
  file: "File",
  doc: "Web page",
  tool_output: "Tool output",
  user: "User's own request",
};

export function channelName(id: string): string {
  return CHANNEL_NAMES[id] ?? id;
}
