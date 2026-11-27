import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";

import type { Data, Study } from "../src/data";
import { renderOverview } from "../src/views/overview";

const dataDir = resolve(__dirname, "../public/data");
const read = <T>(name: string): T => JSON.parse(readFileSync(resolve(dataDir, name), "utf-8")) as T;

function load(): Data {
  return { summary: read("summary.json"), meta: read("meta.json") };
}

function render(data: Data): HTMLElement {
  const main = document.createElement("main");
  renderOverview(main, data);
  return main;
}

beforeEach(() => {
  document.body.replaceChildren();
});

describe("overview", () => {
  it("renders every finding from the exported data without broken values", () => {
    const main = render(load());
    const text = main.textContent ?? "";
    expect(main.querySelectorAll("h2").length).toBe(5);
    for (const bad of ["NaN", "undefined", "null", "Infinity"]) expect(text).not.toContain(bad);
  });

  it("shows model tag and run date next to every set of results", () => {
    const data = load();
    const main = render(data);
    const notes = [...main.querySelectorAll(".provenance")].map((n) => n.textContent ?? "");
    expect(notes.length).toBeGreaterThanOrEqual(4);
    for (const note of notes) expect(note).toMatch(/run(s)? \d{4}-\d{2}-\d{2}/);
    const tag = data.meta.models[0]?.tag ?? "";
    expect(notes.join(" ")).toContain(tag.split("@")[0]?.split("/")[0] ?? "");
  });

  it("takes every k/n in the language table from summary.json", () => {
    const data = load();
    const main = render(data);
    const table = main.querySelector("table");
    const cells = [...(table?.querySelectorAll("td") ?? [])].map((c) => c.textContent ?? "");
    const main_study = data.summary.studies.find((s) => s.id === "main") as Study;
    const known = new Set(
      main_study.pooled.filter((p) => p.channel === "injected").map((p) => `${p.k}/${p.n}`),
    );
    const shown = cells.filter((c) => c !== "not run yet").map((c) => c.split(" ")[0] ?? "");
    expect(shown.length).toBeGreaterThan(0);
    for (const kn of shown) expect(known.has(kn)).toBe(true);
  });

  it("says not run yet, with no numbers, when a study has no data", () => {
    const data = load();
    for (const study of data.summary.studies) {
      study.status = "not_run";
      study.cells = [];
      study.pooled = [];
      study.effects = [];
      study.metrics = {};
    }
    const main = render(data);
    expect(main.querySelectorAll(".not-run").length).toBe(5);
    expect(main.querySelectorAll("table").length).toBe(0);
  });

  it("inserts text as text, never as markup", () => {
    const data = load();
    data.meta.repo_url = "https://example.test/<img src=x onerror=alert(1)>";
    const main = render(data);
    expect(main.querySelector("img")).toBeNull();
  });
});
