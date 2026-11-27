import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Data } from "../src/data";
import { renderDefenses } from "../src/views/defenses";
import { renderHeatmap } from "../src/views/heatmap";
import { ARCHITECTURE, architectureDiagram, renderHow } from "../src/views/how";
import { renderOverview } from "../src/views/overview";
import { renderReplay } from "../src/views/replay";

const root = resolve(__dirname, "..");
const dataDir = resolve(root, "public/data");
const readText = (p: string): string => readFileSync(p, "utf-8");
const data = {
  summary: JSON.parse(readText(resolve(dataDir, "summary.json"))),
  meta: JSON.parse(readText(resolve(dataDir, "meta.json"))),
} as Data;

beforeEach(() => {
  document.body.replaceChildren();
  vi.stubGlobal("fetch", async (url: string) => {
    const rel = String(url).replace(/^.*\/data\//, "");
    return { ok: true, status: 200, json: async () => JSON.parse(readText(resolve(dataDir, rel))) };
  });
});
afterEach(() => vi.unstubAllGlobals());

// ---- WCAG contrast of the design tokens ------------------------------------------------------

function tokens(): Record<string, string> {
  const css = readText(resolve(root, "src/styles/tokens.css"));
  const found = [...css.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)];
  return Object.fromEntries(found.map((m) => [m[1] ?? "", m[2] ?? ""]));
}
function lum(hex: string): number {
  const c = (i: number): number => {
    const v = parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * c(0) + 0.7152 * c(1) + 0.0722 * c(2);
}
function ratio(a: string, b: string): number {
  const [x, y] = [lum(a), lum(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

describe("colour tokens", () => {
  const t = tokens();
  const pairs: [string, string][] = [
    ["text", "bg"],
    ["text", "surface"],
    ["text", "surface-2"],
    ["muted", "bg"],
    ["muted", "surface"],
    ["muted", "surface-2"],
    ["accent", "bg"],
    ["accent", "surface"],
    ["accent", "surface-2"],
    ["accent-ink", "accent"],
  ];
  it.each(pairs)("%s on %s has at least 4.5:1 contrast", (fg, bg) => {
    expect(t[fg]).toBeDefined();
    expect(ratio(t[fg] as string, t[bg] as string)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the focus ring and hairline borders visible", () => {
    expect(ratio(t["accent"] as string, t["bg"] as string)).toBeGreaterThanOrEqual(3);
    expect(ratio(t["border"] as string, t["bg"] as string)).toBeGreaterThanOrEqual(1.3);
  });

  it("honours reduced motion and ships a focus style, skip link and page language", () => {
    const base = readText(resolve(root, "src/styles/base.css"));
    expect(base).toContain("prefers-reduced-motion: reduce");
    expect(base).toContain(":focus-visible");
    const html = readText(resolve(root, "index.html"));
    expect(html).toContain('href="#main"');
    expect(html).toContain('id="main"');
    expect(html).toContain('<html lang="en">');
    expect(html).toContain("width=device-width");
  });
});

// ---- structure of every view -------------------------------------------------------------------

async function views(): Promise<[string, HTMLElement][]> {
  const out: [string, HTMLElement][] = [];
  const add = async (
    name: string,
    draw: (el: HTMLElement) => void | (() => void),
    ready?: string,
  ): Promise<void> => {
    const el = document.createElement("main");
    document.body.append(el);
    draw(el);
    if (ready) await vi.waitFor(() => expect(el.querySelector(ready)).not.toBeNull());
    out.push([name, el]);
  };
  await add("overview", (el) => renderOverview(el, data));
  await add("heatmap", (el) => renderHeatmap(el, data));
  await add("defenses", (el) => renderDefenses(el, data));
  await add("replay", (el) => renderReplay(el, data, "tool-policy-blocked-send"), ".player");
  await add("how", (el) => renderHow(el, data));
  return out;
}

describe("view structure", () => {
  it("has one h1, no skipped heading levels, and no duplicate ids", async () => {
    for (const [name, el] of await views()) {
      expect(el.querySelectorAll("h1").length, name).toBe(1);
      let last = 1;
      for (const heading of el.querySelectorAll("h1,h2,h3,h4")) {
        const level = Number(heading.tagName.slice(1));
        expect(level - last, `${name}: ${heading.textContent}`).toBeLessThanOrEqual(1);
        last = level;
      }
      const ids = [...el.querySelectorAll("[id]")].map((n) => n.id);
      expect(new Set(ids).size, name).toBe(ids.length);
    }
  });

  it("gives every table a caption, every control a label, and every mark a name", async () => {
    for (const [name, el] of await views()) {
      for (const table of el.querySelectorAll("table")) {
        expect(table.querySelector("caption"), name).not.toBeNull();
      }
      for (const control of el.querySelectorAll("select")) {
        expect(el.querySelector(`label[for="${control.id}"]`), `${name}: ${control.id}`).not.toBeNull();
      }
      for (const button of el.querySelectorAll("button")) {
        expect((button.textContent ?? "").trim().length, name).toBeGreaterThan(0);
      }
      for (const img of el.querySelectorAll("[role='img']")) {
        const named = img.getAttribute("aria-label") || img.getAttribute("aria-labelledby");
        expect(named, `${name}: unnamed role=img`).toBeTruthy();
      }
      for (const stop of el.querySelectorAll("[tabindex='0']")) {
        const named =
          stop.getAttribute("aria-label") || (stop.textContent ?? "").trim() || stop.closest("[aria-label]");
        expect(named, `${name}: focusable element without a name`).toBeTruthy();
      }
    }
  });

  it("offers a table or text alternative wherever a chart is drawn", async () => {
    const all = await views();
    const get = (n: string): HTMLElement => all.find(([k]) => k === n)?.[1] as HTMLElement;
    expect(get("heatmap").querySelector("details table")).not.toBeNull();
    expect(get("defenses").querySelectorAll("table").length).toBeGreaterThanOrEqual(2);
    const text = get("how").querySelector("ol")?.textContent ?? "";
    for (const box of ARCHITECTURE) expect(text).toContain(box.title);
  });
});

describe("how it works", () => {
  it("draws every architecture box with an accessible name and description", () => {
    const diagram = architectureDiagram();
    expect(diagram.getAttribute("role")).toBe("img");
    expect(diagram.querySelectorAll(".box").length).toBe(ARCHITECTURE.length);
    expect(diagram.querySelector("title")?.textContent).toBeTruthy();
    expect(diagram.querySelector("desc")?.textContent).toBeTruthy();
  });

  it("contains no result numbers: only the 95% confidence level, never k/n or rates", () => {
    const main = document.createElement("main");
    renderHow(main, data);
    const text = (main.textContent ?? "").replaceAll("95%", "");
    expect(text).not.toMatch(/\d+\/\d+|\d+(\.\d+)?%/);
  });
});

describe("no hard-coded results in the source", () => {
  it("has no k/n counts in the view, chart and logic code", () => {
    const files = ["src/views", "src/charts"].flatMap((d) =>
      readdirSync(resolve(root, d)).map((f) => resolve(root, d, f)),
    );
    files.push(resolve(root, "src/findings.ts"), resolve(root, "src/replay.ts"));
    for (const file of files) {
      const code = readText(file).replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
      expect(code, file).not.toMatch(/["'`][^"'`$]*\b\d+\/\d+\b[^"'`]*["'`]/);
    }
  });
});
