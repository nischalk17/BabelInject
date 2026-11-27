import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Data, Trace } from "../src/data";
import { buildTimeline, segments, verdictAccount } from "../src/replay";
import { PLAY_MS, renderReplay } from "../src/views/replay";

const dataDir = resolve(__dirname, "../public/data");
const readJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(dataDir, rel), "utf-8")) as T;
const traceIds = readdirSync(resolve(dataDir, "traces"))
  .filter((f) => f.endsWith(".json") && f !== "index.json")
  .map((f) => f.replace(/\.json$/, ""));
const trace = (id: string): Trace => readJson<Trace>(`traces/${id}.json`);
const data = { summary: { schema_version: 1, studies: [] }, meta: readJson("meta.json") } as unknown as Data;

function stubFetch(failTraces = false): void {
  vi.stubGlobal("fetch", async (url: string) => {
    const rel = String(url).replace(/^.*\/data\//, "");
    if (failTraces && rel.startsWith("traces/")) throw new Error("network down");
    try {
      const body = JSON.parse(readFileSync(resolve(dataDir, decodeURIComponent(rel)), "utf-8"));
      return { ok: true, status: 200, json: async () => body };
    } catch {
      return { ok: false, status: 404, json: async () => ({}) };
    }
  });
}

async function mount(param?: string): Promise<{ main: HTMLElement; stop: () => void }> {
  const main = document.createElement("main");
  document.body.append(main);
  const stop = renderReplay(main, data, param);
  await vi.waitFor(() => expect(main.querySelector(".player, .error")).not.toBeNull());
  return { main, stop };
}

const visible = (main: HTMLElement): number => main.querySelectorAll(".step:not([hidden])").length;
const click = (main: HTMLElement, label: string): void => {
  const button = [...main.querySelectorAll<HTMLButtonElement>("button")].find((b) => b.textContent === label);
  if (!button) throw new Error(`no button ${label}`);
  button.click();
};

beforeEach(() => {
  document.body.replaceChildren();
  stubFetch();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("replay logic", () => {
  it("builds one timeline entry per step plus the verdict, for every featured trace", () => {
    expect(traceIds.length).toBeGreaterThanOrEqual(8);
    for (const id of traceIds) {
      const t = trace(id);
      const timeline = buildTimeline(t);
      expect(timeline.length).toBe(t.steps.length + 1);
      expect(timeline.at(-1)?.kind).toBe("verdict");
      expect(timeline[0]?.kind).toBe("user");
    }
  });

  it("splits text at the injection spans and loses nothing", () => {
    for (const id of traceIds) {
      const t = trace(id);
      for (const step of t.steps) {
        const parts = segments(step.text, step.injection_spans);
        expect(parts.map((p) => p.text).join("")).toBe(step.text);
        for (const p of parts.filter((x) => x.injected)) expect(p.text).toBe(t.injection?.payload);
      }
    }
    expect(segments("abc", [[1, 2]]).map((s) => s.text)).toEqual(["a", "b", "c"]);
    expect(segments("abc", [[2, 9], [1, 2]]).map((s) => s.injected)).toEqual([false, true, false]);
  });

  it("states the verdict the judge stored, and why", () => {
    for (const id of traceIds) {
      const t = trace(id);
      const account = verdictAccount(t);
      const success = t.verdict.attack_success;
      expect(account.badge).toBe(
        success === null ? "NO ATTACK IN THIS RUN" : success ? "ATTACK EXECUTED" : "ATTACK BLOCKED",
      );
      expect(account.reasons.length).toBeGreaterThan(0);
      if (success) expect(account.reasons.join(" ")).toContain(t.verdict.rule?.matched_email?.subject ?? "?");
    }
    const policy = verdictAccount(trace("tool-policy-blocked-send"));
    expect(policy.reasons.join(" ")).toContain("Blocked by policy");
  });
});

describe("replay view", () => {
  it("opens the requested trace with model, run date and defense, showing only step 1", async () => {
    const { main } = await mount("detector-hi-fails");
    const t = trace("detector-hi-fails");
    expect(main.querySelector("h2")?.textContent).toBe(t.title);
    const facts = main.querySelector(".facts")?.textContent ?? "";
    expect(facts).toContain(t.model_tag);
    expect(facts).toContain(t.run_date ?? "?");
    expect(facts).toContain(t.defense.version);
    expect(visible(main)).toBe(1);
    expect(main.querySelector(".progress")?.textContent).toBe(`Step 1 of ${t.steps.length + 1}`);
    for (const bad of ["NaN", "undefined", "null"]) expect(main.textContent).not.toContain(bad);
  });

  it("steps forward and back, enables the right buttons, and ends on the verdict", async () => {
    const { main } = await mount("tool-policy-blocked-send");
    const total = trace("tool-policy-blocked-send").steps.length + 1;
    const prev = [...main.querySelectorAll<HTMLButtonElement>("button")].find((b) => b.textContent === "Previous");
    expect(prev?.disabled).toBe(true);
    for (let i = 1; i < total; i++) click(main, "Next");
    expect(visible(main)).toBe(total);
    expect(main.querySelector(".badge")?.textContent).toBe("ATTACK BLOCKED");
    expect(main.querySelector(".verdict")?.textContent).toContain("Blocked by policy");
    expect([...main.querySelectorAll<HTMLButtonElement>("button")].find((b) => b.textContent === "Next")?.disabled).toBe(true);
    click(main, "Previous");
    expect(visible(main)).toBe(total - 1);
    click(main, "Restart");
    expect(visible(main)).toBe(1);
  });

  it("highlights exactly the stored attack text, and labels it so colour is not the only cue", async () => {
    const { main } = await mount("en-owner-note-tool-output");
    const t = trace("en-owner-note-tool-output");
    for (let i = 1; i < t.steps.length + 1; i++) click(main, "Next");
    const marks = [...main.querySelectorAll("mark.inj")];
    expect(marks.length).toBeGreaterThan(0);
    for (const m of marks) expect(m.textContent).toBe(t.injection?.payload);
    expect(main.querySelector(".callout .tag")?.textContent).toBe("Hidden instruction");
    expect(main.querySelector(".badge")?.textContent).toBe("ATTACK EXECUTED");
  });

  it("shows defense events and explains a removed result", async () => {
    const en = await mount("detector-en-blocked");
    for (let i = 1; i < trace("detector-en-blocked").steps.length + 1; i++) click(en.main, "Next");
    expect(en.main.querySelector(".defense-note")?.textContent).toContain("the result was removed");
    expect(en.main.querySelector(".verdict .note")?.textContent).toContain("detector removed");
    document.body.replaceChildren();
    const hi = await mount("detector-hi-fails");
    for (let i = 1; i < trace("detector-hi-fails").steps.length + 1; i++) click(hi.main, "Next");
    expect(hi.main.querySelector(".defense-note")?.textContent).toContain("passed on");
    expect(hi.main.querySelector(".badge")?.textContent).toBe("ATTACK EXECUTED");
  });

  it("autoplays one step per interval, pauses on request, and stops at the end", async () => {
    const { main } = await mount("sandwich-en-file");
    const total = trace("sandwich-en-file").steps.length + 1;
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    click(main, "Play");
    expect(main.querySelector("button[aria-pressed]")?.textContent).toBe("Pause");
    vi.advanceTimersByTime(PLAY_MS);
    expect(visible(main)).toBe(2);
    click(main, "Pause");
    vi.advanceTimersByTime(PLAY_MS * 3);
    expect(visible(main)).toBe(2);
    click(main, "Play");
    vi.advanceTimersByTime(PLAY_MS * (total + 2));
    expect(visible(main)).toBe(total);
    expect(main.querySelector("button[aria-pressed]")?.textContent).toBe("Play");
  });

  it("stops autoplay on manual navigation, on arrow keys, and on cleanup", async () => {
    const { main, stop } = await mount("sandwich-en-file");
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    click(main, "Play");
    click(main, "Next");
    vi.advanceTimersByTime(PLAY_MS * 3);
    expect(visible(main)).toBe(2);
    const controls = main.querySelector(".controls") as HTMLElement;
    controls.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(visible(main)).toBe(3);
    controls.dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true }));
    expect(visible(main)).toBe(1);
    click(main, "Play");
    stop();
    vi.advanceTimersByTime(PLAY_MS * 3);
    expect(visible(main)).toBe(1);
  });

  it("announces the current step to screen readers", async () => {
    const { main } = await mount("sandwich-en-file");
    click(main, "Next");
    const live = main.querySelector("[aria-live]");
    expect(live?.textContent).toMatch(/^Step 2 of \d+: /);
    expect(main.querySelector(".step[aria-current='step']")).not.toBeNull();
  });

  it("switches trace from the picker, updates the address, and follows the pair link", async () => {
    const { main } = await mount("sandwich-en-file");
    const select = main.querySelector<HTMLSelectElement>("#f-trace");
    expect(select?.options.length).toBe(traceIds.length);
    if (select) {
      select.value = "detector-en-blocked";
      select.dispatchEvent(new Event("change"));
    }
    await vi.waitFor(() => expect(main.querySelector("h2")?.textContent).toBe(trace("detector-en-blocked").title));
    expect(location.hash).toBe("#/replay/detector-en-blocked");
    main.querySelector<HTMLAnchorElement>("a[data-pair]")?.click();
    await vi.waitFor(() => expect(main.querySelector("h2")?.textContent).toBe(trace("detector-hi-fails").title));
    expect(main.querySelector<HTMLSelectElement>("#f-trace")?.value).toBe("detector-hi-fails");
  });

  it("falls back to the first trace for an unknown id and reports load failures", async () => {
    const first = await mount("no-such-trace");
    expect(first.main.querySelector("h2")).not.toBeNull();
    document.body.replaceChildren();
    stubFetch(true);
    const failed = await mount("sandwich-en-file");
    expect(failed.main.querySelector(".error")?.textContent).toContain("could not be loaded");
  });
});
