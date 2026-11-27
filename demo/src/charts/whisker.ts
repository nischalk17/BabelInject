/** Horizontal point-and-interval marks (error bars) on a shared axis, drawn as small SVGs so the
 * text stays HTML and legible at 360 px. */

import { extent } from "d3-array";
import { scaleLinear } from "d3-scale";

import { h, svg } from "../dom";

export type Domain = readonly [number, number];

/** A shared domain that always contains 0, with a little padding. */
export function sharedDomain(values: readonly number[]): Domain {
  const [lo, hi] = extent([0, ...values]);
  const a = lo ?? 0;
  const b = hi ?? 1;
  const pad = (b - a) * 0.08 || 1;
  return [a - pad, b + pad];
}

function scaleFor(domain: Domain): (v: number) => number {
  const s = scaleLinear().domain([...domain]).range([0, 100]);
  return (v) => s(v);
}

/** Tick labels along the top of a column, positioned by percentage. */
export function axis(domain: Domain, unit: string): HTMLElement {
  const x = scaleFor(domain);
  const ticks = scaleLinear().domain([...domain]).ticks(4);
  return h(
    "div",
    { class: "axis", "aria-hidden": "true" },
    ...ticks.map((t) => h("span", { style: `left:${x(t)}%` }, String(t))),
    h("span", { class: "unit" }, unit),
  );
}

/** One estimate with its interval. `label` is the accessible name (it carries the numbers). */
export function whisker(domain: Domain, value: number, lo: number, hi: number, label: string): SVGElement {
  const x = scaleFor(domain);
  const stroke = (extra: Record<string, string>): Record<string, string> => ({
    "vector-effect": "non-scaling-stroke",
    ...extra,
  });
  return svg(
    "svg",
    { class: "whisker", viewBox: "0 0 100 20", preserveAspectRatio: "none", role: "img", "aria-label": label },
    svg("line", stroke({ x1: String(x(0)), x2: String(x(0)), y1: "0", y2: "20", class: "zero" })),
    svg("line", stroke({ x1: String(x(lo)), x2: String(x(hi)), y1: "10", y2: "10", class: "bar" })),
    svg("line", stroke({ x1: String(x(lo)), x2: String(x(lo)), y1: "5", y2: "15", class: "bar" })),
    svg("line", stroke({ x1: String(x(hi)), x2: String(x(hi)), y1: "5", y2: "15", class: "bar" })),
    svg("line", stroke({ x1: String(x(value)), x2: String(x(value)), y1: "3", y2: "17", class: "point" })),
  );
}
