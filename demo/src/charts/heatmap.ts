/** Language x channel heatmap as an accessible table. Colour is binned (not a smooth ramp) so the
 * printed k/n keeps at least 4.5:1 contrast on every bin; the number is the primary encoding. */

import { scaleThreshold } from "d3-scale";

import type { Cell } from "../data";
import { h } from "../dom";
import { LANGUAGES, kn, languageName, pct } from "../format";
import { type Tooltip, attachTooltip } from "./tooltip";

export const CHANNELS: ReadonlyArray<readonly [string, string]> = [
  ["email", "Email"],
  ["file", "File"],
  ["doc", "Web page"],
  ["tool_output", "Tool output"],
];

export const INK_LIGHT = "#e6e9ee";
export const INK_DARK = "#0b0d10";

/** Bins: exactly 0, up to 10%, up to 25%, up to 50%, above 50%. */
export const BIN_LABELS = ["0%", "up to 10%", "up to 25%", "up to 50%", "above 50%"] as const;
export const BIN_BG = ["#181d24", "#3b3216", "#5f4c1c", "#c9972f", "#f2b84b"] as const;
export const BIN_FG = [INK_LIGHT, INK_LIGHT, INK_LIGHT, INK_DARK, INK_DARK] as const;

const EDGE = 1e-9;
const binOf = scaleThreshold<number, number>()
  .domain([EDGE, 0.1 + EDGE, 0.25 + EDGE, 0.5 + EDGE])
  .range([0, 1, 2, 3, 4]);

export function heatBin(rate: number): { bg: string; fg: string; label: string } {
  const bin = binOf(rate);
  return { bg: BIN_BG[bin] ?? BIN_BG[0], fg: BIN_FG[bin] ?? INK_LIGHT, label: BIN_LABELS[bin] ?? "" };
}

export function cellKey(language: string, channel: string): string {
  return `${language}|${channel}`;
}

/** Tooltip and aria-label text for one cell; every number is read from the export. */
export function cellLines(cell: Cell, channelLabel: string): string[] {
  const a = cell.asr;
  const lines = [
    `${languageName(cell.language)}, ${channelLabel}`,
    `${kn(a)} runs: attacker emailed (${pct(a.rate)})`,
    `95% CI ${pct(a.lo)} to ${pct(a.hi)}; n = ${a.n}`,
  ];
  if (cell.item_opened) lines.push(`Agent opened the injected item: ${kn(cell.item_opened)}`);
  if (cell.attack_attempted) lines.push(`Agent tried to email the attacker: ${kn(cell.attack_attempted)}`);
  if (cell.attacked_utility) lines.push(`Task still completed: ${kn(cell.attacked_utility)}`);
  return lines;
}

export function heatLegend(): HTMLElement {
  return h(
    "ul",
    { class: "legend", "aria-label": "Colour key: attack success rate" },
    ...BIN_LABELS.map((label, i) =>
      h(
        "li",
        {},
        h("span", { class: "swatch", style: `background:${BIN_BG[i]}`, "aria-hidden": "true" }),
        label,
      ),
    ),
    h("li", {}, h("span", { class: "swatch none", "aria-hidden": "true" }), "not run"),
  );
}

export function heatmap(caption: string, cells: Map<string, Cell>, tip: Tooltip): HTMLElement {
  const head = h(
    "tr",
    {},
    h("th", { scope: "col" }, "Language"),
    ...CHANNELS.map(([, label]) => h("th", { scope: "col", class: "right" }, label)),
  );
  const rows = LANGUAGES.map((language) =>
    h(
      "tr",
      {},
      h("th", { scope: "row" }, languageName(language)),
      ...CHANNELS.map(([channel, channelLabel]) => {
        const cell = cells.get(cellKey(language, channel));
        if (!cell) {
          return h("td", { class: "heat-cell empty", "aria-label": `${languageName(language)}, ${channelLabel}: not run` }, "not run");
        }
        const lines = cellLines(cell, channelLabel);
        const bin = heatBin(cell.asr.rate);
        const td = h(
          "td",
          {
            class: "heat-cell",
            tabindex: 0,
            style: `background:${bin.bg};color:${bin.fg}`,
            "aria-label": lines.join(". "),
          },
          h("span", { class: "heat-kn num" }, kn(cell.asr)),
          h("span", { class: "heat-pct num" }, pct(cell.asr.rate)),
        );
        attachTooltip(td, tip, lines);
        return td;
      }),
    ),
  );
  return h(
    "div",
    { class: "table-wrap heat-wrap" },
    h("table", { class: "heat" }, h("caption", {}, caption), h("thead", {}, head), h("tbody", {}, ...rows)),
  );
}
