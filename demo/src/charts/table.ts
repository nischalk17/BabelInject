/** Accessible data table. Every chart in the demo also offers its numbers through this. */

import { h } from "../dom";

export interface Column {
  label: string;
  numeric?: boolean;
}

export interface TableSpec {
  caption: string;
  columns: Column[];
  /** The first cell of each row is rendered as a row header. */
  rows: string[][];
}

export function dataTable(spec: TableSpec): HTMLElement {
  const head = h(
    "tr",
    {},
    ...spec.columns.map((c) => h("th", { scope: "col", class: c.numeric ? "right" : undefined }, c.label)),
  );
  const body = spec.rows.map((row) =>
    h(
      "tr",
      {},
      ...row.map((cell, i) => {
        const column = spec.columns[i];
        const numeric = column?.numeric === true;
        return i === 0
          ? h("th", { scope: "row" }, cell)
          : h("td", { class: numeric ? "right num" : undefined }, cell);
      }),
    ),
  );
  return h(
    "div",
    { class: "table-wrap", role: "region", "aria-label": spec.caption, tabindex: 0 },
    h("table", {}, h("caption", {}, spec.caption), h("thead", {}, head), h("tbody", {}, ...body)),
  );
}
