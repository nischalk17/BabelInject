/** Defenses view: attack reduction against benign-utility cost, each with its interval. */

import { dataTable } from "../charts/table";
import { axis, sharedDomain, whisker } from "../charts/whisker";
import { selectControl } from "../controls";
import type { Data, Effect, PairedRow } from "../data";
import { fill, h } from "../dom";
import {
  LANGUAGES,
  defenseName,
  kn,
  languageName,
  modelLabel,
  provenance,
  signedPp,
  withInterval,
} from "../format";

const DEFENSE_ORDER = ["spotlight", "sandwich", "tool_policy", "detector"];

function order(row: PairedRow): [number, number] {
  return [LANGUAGES.indexOf(row.language as (typeof LANGUAGES)[number]), DEFENSE_ORDER.indexOf(row.defense)];
}

function ppText(value: number, lo: number, hi: number): string {
  return `${value.toFixed(1)} (${lo.toFixed(1)} to ${hi.toFixed(1)})`;
}

function cellWith(label: string, ...children: (Node | string)[]): HTMLElement {
  return h("td", { "data-label": label }, ...children);
}

export function renderDefenses(main: HTMLElement, data: Data): void {
  main.append(
    h("h1", {}, "What the defenses change"),
    h(
      "p",
      {},
      "Each defense is compared with no defense on the same attacked scenarios. The first mark is the drop in attack success; " +
        "the second is the change in success on harmless tasks, which is what the defense costs. Marks show the estimate and its 95% interval; the dashed line is zero.",
    ),
  );
  const study = data.summary.studies.find((s) => s.id === "main");
  const paired = study?.paired ?? [];
  if (study?.status !== "ok" || paired.length === 0) {
    main.append(h("p", { class: "not-run" }, "Defenses: not run yet."));
    return;
  }
  const models = [...new Set(paired.map((p) => p.model_tag))].sort();
  const filters = h("div", { class: "filters" });
  const result = h("div", { class: "chart-box" });
  main.append(filters, result);
  let model = models[0] ?? "";

  const render = (): void => {
    filters.replaceChildren(
      selectControl("f-dmodel", "Model", models.map((m) => ({ value: m, label: modelLabel(m) })), model, (v) => {
        model = v;
        render();
      }),
    );
    const rows = paired
      .filter((p) => p.model_tag === model)
      .sort((a, b) => {
        const [la, da] = order(a);
        const [lb, db] = order(b);
        return la - lb || da - db;
      });
    const effects = new Map<string, Effect>(
      study.effects.filter((e) => e.model_tag === model).map((e) => [`${e.language}|${e.defense}`, e]),
    );
    const hasUtility = effects.size > 0;
    const redDomain = sharedDomain(rows.flatMap((r) => [r.reduction_lo_pp, r.reduction_hi_pp]));
    const utilDomain = sharedDomain([...effects.values()].flatMap((e) => [e.utility_change_lo_pp, e.utility_change_hi_pp]));

    const body = rows.map((r) => {
      const e = effects.get(`${r.language}|${r.defense}`);
      return h(
        "tr",
        {},
        h("th", { scope: "row" }, `${defenseName(r.defense)}, ${languageName(r.language)}`),
        cellWith("Attack success: defended vs none", h("span", { class: "num" }, `${r.k}/${r.n} vs ${r.base_k}/${r.n}`)),
        cellWith(
          "Drop in attack success, pp (95% CI)",
          whisker(redDomain, r.reduction_pp, r.reduction_lo_pp, r.reduction_hi_pp, `Drop in attack success ${ppText(r.reduction_pp, r.reduction_lo_pp, r.reduction_hi_pp)} percentage points`),
          h("span", { class: "num whisker-text" }, ppText(r.reduction_pp, r.reduction_lo_pp, r.reduction_hi_pp)),
        ),
        e
          ? cellWith(
              "Change on harmless tasks, pp (95% CI)",
              whisker(utilDomain, e.utility_change_pp, e.utility_change_lo_pp, e.utility_change_hi_pp, `Change on harmless tasks ${ppText(e.utility_change_pp, e.utility_change_lo_pp, e.utility_change_hi_pp)} percentage points`),
              h("span", { class: "num whisker-text" }, `${signedPp(e.utility_change_pp)} (${e.utility_change_lo_pp.toFixed(1)} to ${e.utility_change_hi_pp.toFixed(1)})`),
            )
          : cellWith("Change on harmless tasks, pp (95% CI)", "not run yet"),
      );
    });

    const head = h(
      "tr",
      {},
      h("th", { scope: "col" }, "Defense, language"),
      h("th", { scope: "col" }, "Attack success, defended vs none"),
      h("th", { scope: "col" }, "Drop in attack success, pp", axis(redDomain, "pp")),
      h("th", { scope: "col" }, "Change on harmless tasks, pp", hasUtility ? axis(utilDomain, "pp") : null),
    );
    const scenarios = [...new Set(rows.map((r) => `attacks: ${r.attacks}; channels: ${r.channels}`))];
    const benign = study.benign.filter((b) => b.model_tag === model);

    fill(
      result,
      h(
        "div",
        { class: "table-wrap", role: "region", "aria-label": "Defense effects", tabindex: 0 },
        h(
          "table",
          { class: "forest" },
          h("caption", {}, `Defense effects on ${modelLabel(model)}. Intervals: Newcombe 95%, which ignores pairing. Scenarios: ${scenarios.join(" | ")}.`),
          h("thead", {}, head),
          h("tbody", {}, ...body),
        ),
      ),
      hasUtility
        ? null
        : h(
            "p",
            { class: "not-run" },
            "Harmless-task utility was not run for the defenses on this model, so the cost is not shown (not run yet).",
          ),
      h(
        "p",
        { class: "note" },
        "The tool policy refuses to email anyone who is not a known contact, so its attack success is 0 by construction; read it as a ceiling, not a measured robustness.",
      ),
      benign.length
        ? dataTable({
            caption: "Harmless tasks completed with each defense (no attack present).",
            columns: [{ label: "Defense" }, { label: "Tasks completed", numeric: true }],
            rows: benign.map((b) => [defenseName(b.defense), withInterval(b.utility)]),
          })
        : null,
      dataTable({
        caption: "Data behind the marks: attack success with and without each defense.",
        columns: [
          { label: "Defense, language" },
          { label: "Defended", numeric: true },
          { label: "No defense", numeric: true },
          { label: "Drop, pp (95% CI)", numeric: true },
        ],
        rows: rows.map((r) => [
          `${defenseName(r.defense)}, ${languageName(r.language)}`,
          kn({ k: r.k, n: r.n }),
          kn({ k: r.base_k, n: r.n }),
          ppText(r.reduction_pp, r.reduction_lo_pp, r.reduction_hi_pp),
        ]),
      }),
      h("p", { class: "provenance" }, `${study.title}. ${provenance(data.meta, [model])}`),
    );
  };
  render();
}
