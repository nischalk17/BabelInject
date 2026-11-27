/** Heatmap view: attack success by language x channel, with filters. */

import { CHANNELS, cellKey, heatLegend, heatmap } from "../charts/heatmap";
import { dataTable } from "../charts/table";
import { createTooltip } from "../charts/tooltip";
import { selectControl } from "../controls";
import type { Cell, Data, Study } from "../data";
import { fill, h } from "../dom";
import {
  LANGUAGES,
  attackName,
  channelName,
  defenseName,
  kn,
  languageName,
  modelLabel,
  pct,
  provenance,
} from "../format";

interface State {
  study: string;
  model: string;
  defense: string;
  attack: string;
}

const INJECTED = new Set(CHANNELS.map(([id]) => id));

function injectedCells(study: Study | undefined): Cell[] {
  return (study?.cells ?? []).filter((c) => INJECTED.has(c.channel));
}

function uniq(values: string[]): string[] {
  return [...new Set(values)].sort();
}

/** Pick `preferred` if it is among the options, else the first option. */
function pick(options: string[], preferred: string): string {
  return options.includes(preferred) ? preferred : (options[0] ?? preferred);
}

export function renderHeatmap(main: HTMLElement, data: Data): void {
  const studies = data.summary.studies.filter((s) => s.status === "ok" && injectedCells(s).length > 0);
  main.append(
    h("h1", {}, "Attack success by language and channel"),
    h(
      "p",
      {},
      "Each cell is the share of runs in which the agent emailed the attacker, for one language and one place the hidden instruction was planted. " +
        "Read each cell with its n: cells with few runs have wide intervals.",
    ),
  );
  const first = studies[0];
  if (!first) {
    main.append(h("p", { class: "not-run" }, "Heatmap: not run yet."));
    return;
  }

  const filters = h("div", { class: "filters" });
  const result = h("div", { class: "chart-box" });
  main.append(filters, result);

  const state: State = { study: first.id, model: "", defense: "none", attack: "ALL" };

  const render = (): void => {
    const study = studies.find((s) => s.id === state.study) ?? first;
    const cells = injectedCells(study);
    const models = uniq(cells.map((c) => c.model_tag));
    if (state.model === "") {
      // First visit: start on the model with the most cells, so the grid is not mostly "not run".
      const count = (m: string): number => cells.filter((c) => c.model_tag === m).length;
      state.model = [...models].sort((a, b) => count(b) - count(a) || a.localeCompare(b))[0] ?? "";
    }
    state.model = pick(models, state.model);
    const forModel = cells.filter((c) => c.model_tag === state.model);
    const defenses = uniq(forModel.map((c) => c.defense));
    state.defense = pick(defenses, state.defense);
    const forDefense = forModel.filter((c) => c.defense === state.defense);
    const attacks = uniq(forDefense.map((c) => c.attack)).sort((a, b) => (a === "ALL" ? -1 : b === "ALL" ? 1 : a.localeCompare(b)));
    state.attack = pick(attacks, state.attack);

    filters.replaceChildren(
      selectControl("f-study", "Study", studies.map((s) => ({ value: s.id, label: s.title })), study.id, (v) => {
        state.study = v;
        render();
      }),
      selectControl("f-model", "Model", models.map((m) => ({ value: m, label: modelLabel(m) })), state.model, (v) => {
        state.model = v;
        render();
      }),
      selectControl("f-defense", "Defense", defenses.map((d) => ({ value: d, label: defenseName(d) })), state.defense, (v) => {
        state.defense = v;
        render();
      }),
      selectControl("f-attack", "Attack", attacks.map((a) => ({ value: a, label: attackName(a) })), state.attack, (v) => {
        state.attack = v;
        render();
      }),
    );

    const selected = forDefense.filter((c) => c.attack === state.attack);
    const byKey = new Map(selected.map((c) => [cellKey(c.language, c.channel), c]));
    const caption = `${modelLabel(state.model)}, ${defenseName(state.defense)}, ${attackName(state.attack)}. Number in each cell: runs where the attacker was emailed / runs.`;
    const tip = createTooltip(result);
    const rows = LANGUAGES.flatMap((language) =>
      CHANNELS.map(([channel]) => {
        const cell = byKey.get(cellKey(language, channel));
        return [
          `${languageName(language)}, ${channelName(channel)}`,
          cell ? kn(cell.asr) : "not run yet",
          cell ? pct(cell.asr.rate) : "not run yet",
          cell ? `${pct(cell.asr.lo)} to ${pct(cell.asr.hi)}` : "not run yet",
        ];
      }),
    );
    fill(
      result,
      byKey.size === 0 ? h("p", { class: "not-run" }, "No runs for this selection: not run yet.") : null,
      heatmap(caption, byKey, tip),
      heatLegend(),
      h(
        "details",
        { class: "data-details" },
        h("summary", {}, "Show as a data table"),
        dataTable({
          caption: `Data behind the heatmap: ${caption}`,
          columns: [
            { label: "Language, channel" },
            { label: "Attacker emailed", numeric: true },
            { label: "Rate", numeric: true },
            { label: "95% CI", numeric: true },
          ],
          rows,
        }),
      ),
      h("p", { class: "provenance" }, `${study.title}. ${provenance(data.meta, [state.model])}`),
      tip.el,
    );
  };
  render();
}
