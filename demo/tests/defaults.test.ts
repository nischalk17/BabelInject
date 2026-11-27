import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";

import type { Data, Study } from "../src/data";
import { renderDefenses } from "../src/views/defenses";
import { renderHeatmap } from "../src/views/heatmap";
import { wrap } from "../src/views/how";

const dataDir = resolve(__dirname, "../public/data");
const read = <T>(name: string): T => JSON.parse(readFileSync(resolve(dataDir, name), "utf-8")) as T;
const load = (): Data => ({ summary: read("summary.json"), meta: read("meta.json") });
const mainStudy = (d: Data): Study => d.summary.studies.find((s) => s.id === "main") as Study;

beforeEach(() => document.body.replaceChildren());

function mount(render: (el: HTMLElement, d: Data) => void, d: Data): HTMLElement {
  const main = document.createElement("main");
  document.body.append(main);
  render(main, d);
  return main;
}

describe("first view", () => {
  it("starts the heatmap on the model with the most cells", () => {
    const d = load();
    const cells = mainStudy(d).cells.filter((c) => c.channel !== "user");
    const counts = new Map<string, number>();
    for (const c of cells) counts.set(c.model_tag, (counts.get(c.model_tag) ?? 0) + 1);
    const most = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0];
    const main = mount(renderHeatmap, d);
    expect(main.querySelector<HTMLSelectElement>("#f-model")?.value).toBe(most);
  });

  it("starts the defenses view on a model whose cost was measured, so both marks show", () => {
    const d = load();
    const main = mount(renderDefenses, d);
    const tag = main.querySelector<HTMLSelectElement>("#f-dmodel")?.value ?? "";
    expect(mainStudy(d).effects.some((e) => e.model_tag === tag)).toBe(true);
    expect(main.querySelectorAll("svg.whisker").length).toBe(
      mainStudy(d).paired.filter((p) => p.model_tag === tag).length * 2,
    );
  });
});

describe("diagram text wrapping", () => {
  it("keeps every word and never exceeds the width except for one long word", () => {
    const text = "fake inbox, files, web pages; sending only writes to an outbox";
    const lines = wrap(text, 30);
    expect(lines.join(" ")).toBe(text);
    for (const line of lines) expect(line.length).toBeLessThanOrEqual(30);
    expect(wrap("", 10)).toEqual([]);
    expect(wrap("unbreakable", 3)).toEqual(["unbreakable"]);
  });
});
