import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/views.css";

import { loadData } from "./data";
import { h } from "./dom";
import { startRouter } from "./router";
import { renderDefenses } from "./views/defenses";
import { renderHeatmap } from "./views/heatmap";
import { renderOverview } from "./views/overview";
import { renderReplay } from "./views/replay";

async function boot(): Promise<void> {
  const main = document.getElementById("main");
  const nav = document.getElementById("nav");
  const footer = document.getElementById("footer");
  if (!main || !nav || !footer) throw new Error("page shell is missing");

  let data;
  try {
    data = await loadData();
  } catch (error) {
    main.replaceChildren(
      h(
        "div",
        { class: "error", role: "alert" },
        h("h1", {}, "The data could not be loaded"),
        h("p", {}, String(error)),
        h("p", {}, "Generate it with make demo-data, then rebuild."),
      ),
    );
    return;
  }

  footer.replaceChildren(
    h(
      "p",
      {},
      `Every number comes from the project's results via analysis/export_demo_data.py (commit ${data.meta.git_commit.slice(0, 7)}). Fictional data; no model is called in this page.`,
    ),
    h("p", {}, h("a", { href: data.meta.repo_url }, "Source code"), " | ", h("a", { href: data.meta.report_url }, "Report")),
  );

  startRouter(
    [
      {
        id: "overview",
        label: "Overview",
        title: "Overview",
        render: (el) => renderOverview(el, data),
      },
      {
        id: "heatmap",
        label: "Heatmap",
        title: "Heatmap",
        render: (el) => renderHeatmap(el, data),
      },
      {
        id: "defenses",
        label: "Defenses",
        title: "Defenses",
        render: (el) => renderDefenses(el, data),
      },
      {
        id: "replay",
        label: "Trace replay",
        title: "Trace replay",
        render: (el, param) => renderReplay(el, data, param),
      },
    ],
    nav,
    main,
  );
}

void boot();
