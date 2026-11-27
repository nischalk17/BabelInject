import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";

import { BIN_BG, BIN_FG, heatBin } from "../src/charts/heatmap";
import type { Cell, Data, PairedRow, Study } from "../src/data";
import { kn } from "../src/format";
import { renderDefenses } from "../src/views/defenses";
import { renderHeatmap } from "../src/views/heatmap";

const dataDir = resolve(__dirname, "../public/data");
const read = <T>(name: string): T => JSON.parse(readFileSync(resolve(dataDir, name), "utf-8")) as T;
const load = (): Data => ({ summary: read("summary.json"), meta: read("meta.json") });
const mainStudy = (d: Data): Study => d.summary.studies.find((s) => s.id === "main") as Study;

function choose(root: HTMLElement, id: string, value: string): void {
  const select = root.querySelector<HTMLSelectElement>(`#${id}`);
  if (!select) throw new Error(`no select ${id}`);
  select.value = value;
  select.dispatchEvent(new Event("change"));
}

function mount(render: (el: HTMLElement, d: Data) => void, d: Data): HTMLElement {
  const main = document.createElement("main");
  document.body.append(main);
  render(main, d);
  return main;
}

beforeEach(() => document.body.replaceChildren());

function luminance(hex: string): number {
  const channel = (i: number): number => {
    const v = parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2);
}

describe("heatmap", () => {
  it("keeps at least 4.5:1 contrast between every bin colour and its text", () => {
    for (const [i, bg] of BIN_BG.entries()) {
      const a = luminance(bg);
      const b = luminance(BIN_FG[i] ?? "#ffffff");
      const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    }
    expect(heatBin(0).bg).toBe(BIN_BG[0]);
    expect(heatBin(1).bg).toBe(BIN_BG[4]);
    expect(heatBin(0.1).bg).toBe(BIN_BG[1]); // the boundary belongs to the lower bin
    expect(heatBin(0.1001).bg).toBe(BIN_BG[2]);
  });

  it("shows k/n for every language and channel exactly as exported", () => {
    const d = load();
    const tag = mainStudy(d).cells.find((c) => c.model_tag.includes("qwen2.5:7b"))?.model_tag ?? "";
    const main = mount(renderHeatmap, d);
    choose(main, "f-model", tag);
    const cells = mainStudy(d).cells.filter(
      (c) => c.model_tag === tag && c.defense === "none" && c.attack === "ALL" && c.channel !== "user",
    );
    expect(cells.length).toBe(20);
    const shown = [...main.querySelectorAll(".heat-cell:not(.empty) .heat-kn")].map((e) => e.textContent);
    expect(shown.sort()).toEqual(cells.map((c: Cell) => kn(c.asr)).sort());
    const nan = main.textContent ?? "";
    for (const bad of ["NaN", "undefined", "null"]) expect(nan).not.toContain(bad);
  });

  it("explains each cell with n and the interval, on focus and for screen readers", () => {
    const d = load();
    const main = mount(renderHeatmap, d);
    choose(main, "f-model", mainStudy(d).cells.find((c) => c.model_tag.includes("qwen2.5:7b"))?.model_tag ?? "");
    const cell = main.querySelector<HTMLElement>(".heat-cell:not(.empty)");
    expect(cell?.getAttribute("aria-label")).toMatch(/95% CI .* to .*; n = \d+/);
    cell?.dispatchEvent(new Event("focus"));
    const tip = main.querySelector<HTMLElement>(".tooltip");
    expect(tip?.hidden).toBe(false);
    expect(tip?.textContent).toMatch(/95% CI/);
    cell?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(tip?.hidden).toBe(true);
  });

  it("marks combinations that were never run as not run, with no numbers", () => {
    const d = load();
    const main = mount(renderHeatmap, d);
    const tag = mainStudy(d).cells.find((c) => c.model_tag.includes("qwen2.5:7b"))?.model_tag ?? "";
    choose(main, "f-model", tag);
    choose(main, "f-defense", "detector");
    const empty = [...main.querySelectorAll(".heat-cell.empty")];
    expect(empty.length).toBeGreaterThan(0);
    for (const e of empty) expect(e.textContent).toBe("not run");
  });

  it("has a data table with one row per language and channel", () => {
    const main = mount(renderHeatmap, load());
    expect(main.querySelectorAll("details table tbody tr").length).toBe(20);
  });

  it("says not run yet when no study has data", () => {
    const d = load();
    for (const s of d.summary.studies) s.status = "not_run";
    const main = mount(renderHeatmap, d);
    expect(main.querySelector(".not-run")?.textContent).toContain("not run yet");
    expect(main.querySelector("table")).toBeNull();
  });
});

describe("defenses", () => {
  const rowsFor = (d: Data, model: string): PairedRow[] =>
    mainStudy(d).paired.filter((p) => p.model_tag === model);

  it("lists one row per defense and language with the exported counts and intervals", () => {
    const d = load();
    const tag = mainStudy(d).paired.find((p) => p.model_tag.includes("qwen2.5:7b"))?.model_tag ?? "";
    const main = mount(renderDefenses, d);
    choose(main, "f-dmodel", tag);
    const rows = [...main.querySelectorAll("table.forest tbody tr")];
    const expected = rowsFor(d, tag);
    expect(rows.length).toBe(expected.length);
    for (const p of expected) {
      const text = main.querySelector("table.forest")?.textContent ?? "";
      expect(text).toContain(`${p.k}/${p.n} vs ${p.base_k}/${p.n}`);
      expect(text).toContain(`${p.reduction_pp.toFixed(1)} (${p.reduction_lo_pp.toFixed(1)} to ${p.reduction_hi_pp.toFixed(1)})`);
    }
    expect(main.querySelectorAll("svg.whisker").length).toBe(rows.length * 2); // reduction + cost
  });

  it("shows the cost as not run yet where harmless tasks were not run", () => {
    const d = load();
    const withEffects = new Set(mainStudy(d).effects.map((e) => e.model_tag));
    const tag = mainStudy(d).paired.find((p) => !withEffects.has(p.model_tag))?.model_tag ?? "";
    expect(tag).not.toBe("");
    const main = mount(renderDefenses, d);
    choose(main, "f-dmodel", tag);
    const rows = rowsFor(d, tag).length;
    expect(main.querySelectorAll("svg.whisker").length).toBe(rows); // reduction only
    expect(main.querySelector(".not-run")?.textContent).toContain("not run yet");
    expect(main.textContent).toContain("not run yet");
  });

  it("gives every mark an accessible name with its numbers and offers a data table", () => {
    const main = mount(renderDefenses, load());
    for (const mark of main.querySelectorAll("svg.whisker")) {
      expect(mark.getAttribute("role")).toBe("img");
      expect(mark.getAttribute("aria-label")).toMatch(/percentage points/);
    }
    expect(main.querySelectorAll("table").length).toBeGreaterThanOrEqual(2);
  });
});
