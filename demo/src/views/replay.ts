/** Trace replay: step through one real run, from the user's task to the judge's verdict. */

import { selectControl } from "../controls";
import { type Data, type Trace, type TraceIndexEntry, loadTrace, loadTraceIndex } from "../data";
import { fill, h } from "../dom";
import { attackName, channelName, defenseName, languageName } from "../format";
import { type TimelineStep, buildTimeline, eventText, segments, verdictAccount } from "../replay";

/** Autoplay advances one step per interval. It is never on by default. */
export const PLAY_MS = 1600;

function marked(text: string, spans: number[][]): (Node | string)[] {
  return segments(text, spans).map((s) => (s.injected ? h("mark", { class: "inj" }, s.text) : s.text));
}

function facts(trace: Trace): HTMLElement {
  const s = trace.scenario;
  const rows: [string, string][] = [
    ["Model", trace.model_tag],
    ["Run date", trace.run_date ?? "not recorded"],
    ["Defense", `${defenseName(trace.defense.name)} (${trace.defense.version})`],
    [
      "Attack",
      s.attack_id
        ? `${attackName(s.attack_id)}, ${languageName(s.language ?? "")}, planted in: ${channelName(s.channel ?? "")}`
        : "none (benign run)",
    ],
    ["Scenario", s.scenario_id],
    ["Settings", `prompt ${trace.prompt_version}, config ${trace.config_name ?? "unknown"}`],
  ];
  return h(
    "dl",
    { class: "facts" },
    ...rows.flatMap(([k, v]) => [h("dt", {}, k), h("dd", { class: k === "Model" || k === "Scenario" ? "mono" : "" }, v)]),
  );
}

function verdictCard(trace: Trace): HTMLElement {
  const account = verdictAccount(trace);
  const v = trace.verdict;
  const badgeClass = account.executed === true ? "executed" : account.executed === false ? "blocked" : "none";
  return h(
    "div",
    { class: "verdict" },
    h("p", {}, h("span", { class: `badge ${badgeClass}` }, account.badge)),
    h("ul", { class: "plain" }, ...account.reasons.map((r) => h("li", {}, r))),
    h("p", { class: "label" }, v.utility_success ? "Task completed" : "Task not completed"),
    h(
      "ul",
      { class: "plain" },
      ...v.utility_checks.map((c) =>
        h("li", {}, h("span", { class: "mono" }, c.passed ? "PASS " : "FAIL "), c.text),
      ),
    ),
    trace.injection && !trace.injection.located && trace.injection.note
      ? h("p", { class: "note" }, trace.injection.note)
      : null,
  );
}

function stepCard(trace: Trace, t: TimelineStep, index: number, total: number): HTMLElement {
  const label = h("p", { class: "label step-label" }, `Step ${index + 1} of ${total}: ${t.label}`);
  if (t.kind === "verdict") return h("li", { class: "step", "data-kind": "verdict" }, label, verdictCard(trace));
  const step = t.step;
  if (!step) return h("li", { class: "step" }, label);
  const hidden = trace.injection && step.injection_spans.length > 0;
  return h(
    "li",
    { class: "step", "data-kind": t.kind },
    label,
    hidden && trace.injection
      ? h(
          "p",
          { class: "callout" },
          h("span", { class: "tag" }, "Hidden instruction"),
          trace.scenario.channel === "user"
            ? " In this control, the attack text is the user's own request."
            : ` ${languageName(trace.injection.language)} text planted in the ${channelName(trace.injection.channel).toLowerCase()} data; the agent receives it as part of the data. It is highlighted below.`,
        )
      : null,
    step.text
      ? h("pre", { class: "step-text", tabindex: 0 }, ...marked(step.text, step.injection_spans))
      : null,
    ...(step.events ?? []).map((e) => h("p", { class: "defense-note" }, h("span", { class: "tag" }, "Defense"), ` ${eventText(e)}`)),
  );
}

interface Player {
  el: HTMLElement;
  stop: () => void;
}

function player(trace: Trace): Player {
  const timeline = buildTimeline(trace);
  const total = timeline.length;
  let cur = 0;
  let timer: ReturnType<typeof setInterval> | undefined;

  const cards = timeline.map((t, i) => stepCard(trace, t, i, total));
  const list = h("ol", { class: "timeline" }, ...cards);
  const live = h("p", { class: "sr-only", role: "status", "aria-live": "polite" });
  const progress = h("p", { class: "label progress" });
  const prev = h("button", { type: "button", class: "btn" }, "Previous");
  const next = h("button", { type: "button", class: "btn" }, "Next");
  const play = h("button", { type: "button", class: "btn primary", "aria-pressed": "false" }, "Play");
  const restart = h("button", { type: "button", class: "btn" }, "Restart");

  const stop = (): void => {
    if (timer !== undefined) clearInterval(timer);
    timer = undefined;
    play.textContent = "Play";
    play.setAttribute("aria-pressed", "false");
  };

  const show = (): void => {
    cards.forEach((card, i) => {
      card.hidden = i > cur;
      if (i === cur) card.setAttribute("aria-current", "step");
      else card.removeAttribute("aria-current");
    });
    prev.disabled = cur === 0;
    next.disabled = cur === total - 1;
    const label = timeline[cur]?.label ?? "";
    progress.textContent = `Step ${cur + 1} of ${total}`;
    live.textContent = `Step ${cur + 1} of ${total}: ${label}`;
    const current = cards[cur];
    if (current && typeof current.scrollIntoView === "function") current.scrollIntoView({ block: "nearest" });
  };

  const go = (to: number): void => {
    cur = Math.min(Math.max(to, 0), total - 1);
    show();
  };

  prev.addEventListener("click", () => {
    stop();
    go(cur - 1);
  });
  next.addEventListener("click", () => {
    stop();
    go(cur + 1);
  });
  restart.addEventListener("click", () => {
    stop();
    go(0);
  });
  play.addEventListener("click", () => {
    if (timer !== undefined) {
      stop();
      return;
    }
    if (cur === total - 1) go(0);
    play.textContent = "Pause";
    play.setAttribute("aria-pressed", "true");
    timer = setInterval(() => {
      if (cur >= total - 1) {
        stop();
        return;
      }
      go(cur + 1);
      if (cur >= total - 1) stop();
    }, PLAY_MS);
  });

  const controls = h("div", { class: "controls", role: "group", "aria-label": "Replay controls" }, restart, prev, play, next);
  controls.addEventListener("keydown", (event) => {
    const key = event.key;
    if (key === "ArrowRight") {
      stop();
      go(cur + 1);
    } else if (key === "ArrowLeft") {
      stop();
      go(cur - 1);
    } else if (key === "Home") {
      stop();
      go(0);
    } else if (key === "End") {
      stop();
      go(total - 1);
    } else return;
    event.preventDefault();
  });

  show();
  const system = h(
    "details",
    { class: "data-details" },
    h("summary", {}, "System prompt the model was given"),
    h("pre", { class: "step-text", tabindex: 0 }, trace.system_prompt),
  );
  return { el: h("div", { class: "player" }, controls, progress, live, list, system), stop };
}

export function renderReplay(main: HTMLElement, _data: Data, param?: string): () => void {
  main.append(
    h("h1", {}, "Trace replay"),
    h(
      "p",
      {},
      "Step through one real run: the user's task, the instruction hidden in the data (highlighted), what the agent did, " +
        "and how the deterministic judge decided whether the attack worked. Nothing here is generated; each trace is a stored run.",
    ),
  );
  const picker = h("div", { class: "filters" });
  const body = h("div", { class: "replay-body" }, h("p", { class: "status", role: "status" }, "Loading traces."));
  main.append(picker, body);

  let active: Player | undefined;
  let token = 0;
  const stop = (): void => {
    token += 1;
    active?.stop();
  };

  const open = async (index: TraceIndexEntry[], id: string): Promise<void> => {
    const mine = ++token;
    active?.stop();
    fill(body, h("p", { class: "status", role: "status" }, "Loading trace."));
    try {
      const trace = await loadTrace(id);
      if (mine !== token) return;
      active = player(trace);
      const pair = trace.pair_with ? index.find((e) => e.id === trace.pair_with) : undefined;
      fill(
        body,
        h("h2", {}, trace.title),
        h("p", {}, trace.why_featured),
        pair
          ? h("p", {}, "Compare with: ", h("a", { href: `#/replay/${pair.id}`, "data-pair": pair.id }, pair.title))
          : null,
        facts(trace),
        active.el,
      );
      const link = body.querySelector<HTMLAnchorElement>("a[data-pair]");
      link?.addEventListener("click", (event) => {
        event.preventDefault();
        history.replaceState(null, "", `#/replay/${link.dataset["pair"] ?? ""}`);
        void open(index, link.dataset["pair"] ?? "");
        render(index, link.dataset["pair"] ?? "");
      });
    } catch (error) {
      if (mine !== token) return;
      fill(body, h("p", { class: "error", role: "alert" }, `This trace could not be loaded: ${String(error)}`));
    }
  };

  const render = (index: TraceIndexEntry[], id: string): void => {
    fill(
      picker,
      selectControl("f-trace", "Trace", index.map((e) => ({ value: e.id, label: e.title })), id, (value) => {
        history.replaceState(null, "", `#/replay/${value}`);
        void open(index, value);
      }),
    );
  };

  void loadTraceIndex().then(
    (index) => {
      const first = index[0];
      if (!first) {
        fill(body, h("p", { class: "not-run" }, "Traces: not run yet."));
        return;
      }
      const id = index.some((e) => e.id === param) ? (param as string) : first.id;
      render(index, id);
      void open(index, id);
    },
    (error: unknown) => fill(body, h("p", { class: "error", role: "alert" }, `The trace list could not be loaded: ${String(error)}`)),
  );

  return stop;
}
