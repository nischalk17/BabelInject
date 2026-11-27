/** Selecting rows from summary.json for the Overview. Pure functions; nothing is computed
 * except sums of k and n, which are exact. Intervals always come from the export. */

import type { CountRow, Study } from "./data";
import { LANGUAGES } from "./format";

export type Scope = "injected" | "user";
export type ByModel = Map<string, Map<string, CountRow>>;

/** model tag -> language (including "ALL") -> pooled ASR row for one defense and scope. */
export function pooledLookup(study: Study | undefined, scope: Scope, defense = "none"): ByModel {
  const out: ByModel = new Map();
  for (const row of study?.pooled ?? []) {
    if (row.defense !== defense || row.channel !== scope) continue;
    const byLanguage = out.get(row.model_tag) ?? new Map<string, CountRow>();
    byLanguage.set(row.language, row);
    out.set(row.model_tag, byLanguage);
  }
  return out;
}

/** Highest and lowest language by rate (ties go to the first language in project order). */
export function extremes(byLanguage: Map<string, CountRow>): { high: CountRow; low: CountRow } | null {
  let high: CountRow | undefined;
  let low: CountRow | undefined;
  for (const language of LANGUAGES) {
    const row = byLanguage.get(language);
    if (!row) continue;
    if (!high || row.rate > high.rate) high = row;
    if (!low || row.rate < low.rate) low = row;
  }
  return high && low ? { high, low } : null;
}

export function sumCounts(rows: readonly { k: number; n: number }[]): { k: number; n: number } {
  return rows.reduce((acc, r) => ({ k: acc.k + r.k, n: acc.n + r.n }), { k: 0, n: 0 });
}

export interface DetectorLanguageRow {
  language: string;
  attacked: { k: number; n: number } | null;
  harmless: { k: number; n: number } | null;
}

/** Detector flag counts per language, summed over channels (attacked text and harmless text). */
export function detectorByLanguage(study: Study | undefined): DetectorLanguageRow[] {
  const attacked = study?.metrics["detector_flagged"] ?? [];
  const harmless = study?.metrics["detector_flagged_benign"] ?? [];
  return LANGUAGES.map((language) => {
    const a = attacked.filter((r) => r.language === language);
    const b = harmless.filter((r) => r.language === language);
    return {
      language,
      attacked: a.length ? sumCounts(a) : null,
      harmless: b.length ? sumCounts(b) : null,
    };
  });
}

export function modelTags(by: ByModel): string[] {
  return [...by.keys()].sort();
}
