/** Overview: the question, and findings computed from summary.json (no typed numbers). */

import { dataTable } from "../charts/table";
import { type Data, type Study, studyById } from "../data";
import { h } from "../dom";
import {
  type ByModel,
  detectorByLanguage,
  extremes,
  modelTags,
  pooledLookup,
} from "../findings";
import {
  LANGUAGES,
  defenseName,
  kn,
  languageName,
  modelLabel,
  pct,
  provenance,
  signedPp,
  withInterval,
} from "../format";

const NOT_RUN = "not run yet";

function notRun(what: string): HTMLElement {
  return h("p", { class: "not-run" }, `${what}: ${NOT_RUN}.`);
}

function finding(title: string, measure: string, ...body: (HTMLElement | null)[]): HTMLElement {
  const id = `f-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return h(
    "section",
    { class: "finding", "aria-labelledby": id },
    h("h2", { id }, title),
    h("p", { class: "measure" }, measure),
    ...body,
  );
}

/** Languages as rows, one column per model; "not run yet" where a cell has no data. */
function languageByModel(caption: string, by: ByModel, tags: string[]): HTMLElement {
  const rows = [...LANGUAGES, "ALL"].map((language) => [
    languageName(language),
    ...tags.map((tag) => {
      const row = by.get(tag)?.get(language);
      return row ? withInterval(row) : NOT_RUN;
    }),
  ]);
  return dataTable({
    caption,
    columns: [{ label: "Language" }, ...tags.map((tag) => ({ label: modelLabel(tag), numeric: true }))],
    rows,
  });
}

function languageGap(data: Data, main: Study | undefined): HTMLElement {
  const title = "Attack success by language, no defense";
  const measure =
    "Share of attacked runs in which the agent emailed the attacker, pooled over the attack " +
    "templates and the four channels (email, file, web page, tool output).";
  const by = pooledLookup(main, "injected");
  const tags = modelTags(by);
  if (main?.status !== "ok" || tags.length === 0) return finding(title, measure, notRun(title));
  const lines = tags.flatMap((tag) => {
    const e = extremes(by.get(tag) ?? new Map());
    return e
      ? [
          h(
            "li",
            {},
            `${modelLabel(tag)}: highest for ${languageName(e.high.language)} (${kn(e.high)}, ${pct(e.high.rate)}); ` +
              `lowest for ${languageName(e.low.language)} (${kn(e.low)}, ${pct(e.low.rate)}).`,
          ),
        ]
      : [];
  });
  return finding(
    title,
    measure,
    h("ul", { class: "plain" }, ...lines),
    languageByModel(`Attack success by language (${tags.map(modelLabel).join(", ")})`, by, tags),
    h("p", { class: "provenance" }, provenance(data.meta, tags)),
  );
}

function directRequests(data: Data, main: Study | undefined): HTMLElement {
  const title = "Does the model follow the same text when the user asks directly?";
  const measure =
    "The attack text is given as the user's own request. If the model follows it here but not " +
    "when it is injected, low injected success is not a reading problem.";
  const by = pooledLookup(main, "user");
  const tags = modelTags(by);
  if (main?.status !== "ok" || tags.length === 0) return finding(title, measure, notRun(title));
  const lines = tags.flatMap((tag) => {
    const all = by.get(tag)?.get("ALL");
    return all ? [h("li", {}, `${modelLabel(tag)}: followed ${withInterval(all)} of direct requests.`)] : [];
  });
  return finding(
    title,
    measure,
    h("ul", { class: "plain" }, ...lines),
    languageByModel(`Direct requests followed (${tags.map(modelLabel).join(", ")})`, by, tags),
    h("p", { class: "provenance" }, provenance(data.meta, tags)),
  );
}

function defenses(data: Data, main: Study | undefined): HTMLElement {
  const title = "What the defenses change";
  const measure =
    "Each defense against no defense on the same scenarios: the drop in attack success, and the " +
    "change in success on harmless tasks (the cost).";
  const effects = main?.effects ?? [];
  if (main?.status !== "ok" || effects.length === 0) return finding(title, measure, notRun(title));
  const tags = [...new Set(effects.map((e) => e.model_tag))].sort();
  const rows = effects.map((e) => [
    `${modelLabel(e.model_tag)}, ${defenseName(e.defense)}, ${languageName(e.language)}`,
    `${e.asr_k}/${e.asr_n}`,
    `${e.base_asr_k}/${e.base_asr_n}`,
    `${e.reduction_pp.toFixed(1)} pp (${e.reduction_lo_pp.toFixed(1)} to ${e.reduction_hi_pp.toFixed(1)})`,
    `${signedPp(e.utility_change_pp)} (${e.utility_change_lo_pp.toFixed(1)} to ${e.utility_change_hi_pp.toFixed(1)})`,
  ]);
  return finding(
    title,
    measure,
    dataTable({
      caption:
        "Defense effects. Intervals are Newcombe 95% and ignore pairing. Benign utility is measured per defense, not per language.",
      columns: [
        { label: "Model, defense, language" },
        { label: "Attack success, defended", numeric: true },
        { label: "Attack success, no defense", numeric: true },
        { label: "Reduction, pp (95% CI)", numeric: true },
        { label: "Benign utility change (95% CI)", numeric: true },
      ],
      rows,
    }),
    h("p", { class: "provenance" }, provenance(data.meta, tags)),
  );
}

function detectorLanguages(data: Data, study: Study | undefined): HTMLElement {
  const title = "Does the detector recognise injected text in every language?";
  const measure =
    "A prompted detector (an English prompt) is asked whether each tool result contains instructions. " +
    "Counts are summed over the file and tool-output channels, for attacked text and for harmless text.";
  if (study?.status !== "ok") return finding(title, measure, notRun(title));
  const rows = detectorByLanguage(study).map((r) => [
    languageName(r.language),
    r.attacked ? kn(r.attacked) : NOT_RUN,
    r.harmless ? kn(r.harmless) : NOT_RUN,
  ]);
  const tags = [...new Set((study.metrics["detector_flagged"] ?? []).map((r) => r.model_tag))].sort();
  return finding(
    title,
    measure,
    dataTable({
      caption: "Detector said YES (flagged) on attacked text and on harmless text, by language.",
      columns: [
        { label: "Language" },
        { label: "Flagged, attacked", numeric: true },
        { label: "Flagged, harmless", numeric: true },
      ],
      rows,
    }),
    h("p", { class: "provenance" }, provenance(data.meta, tags)),
  );
}

function addressOnly(data: Data, quiet: Study | undefined): HTMLElement {
  const title = "Is the attacker address why the large model refuses?";
  const measure =
    "The same attack text with a plain-looking recipient address instead of an obviously malicious one.";
  const by = pooledLookup(quiet, "injected");
  const tags = modelTags(by);
  if (quiet?.status !== "ok" || tags.length === 0) return finding(title, measure, notRun(title));
  const lines = tags.flatMap((tag) => {
    const all = by.get(tag)?.get("ALL");
    return all ? [h("li", {}, `${modelLabel(tag)}: ${withInterval(all)} of injected runs succeeded.`)] : [];
  });
  return finding(
    title,
    measure,
    h("ul", { class: "plain" }, ...lines),
    languageByModel(`Attack success with a plain address (${tags.map(modelLabel).join(", ")})`, by, tags),
    h("p", { class: "provenance" }, provenance(data.meta, tags)),
  );
}

export function renderOverview(main: HTMLElement, data: Data): void {
  const study = (id: string): Study | undefined => studyById(data, id);
  main.append(
    h(
      "section",
      { class: "hero" },
      h("h1", {}, "Do prompt-injection defenses hold across languages?"),
      h(
        "p",
        { class: "lead" },
        "Hidden instructions in an email, file, web page or tool result can make an AI agent send an email to an attacker. " +
          "This project measures how often that works in English, Nepali, romanized Nepali, Hindi and code-mixed text, and how much four defenses help and cost.",
      ),
      h(
        "ul",
        { class: "links" },
        h("li", {}, h("a", { href: data.meta.repo_url }, "Repository")),
        h("li", {}, h("a", { href: data.meta.report_url }, "Report")),
      ),
    ),
    languageGap(data, study("main")),
    directRequests(data, study("main")),
    defenses(data, study("main")),
    detectorLanguages(data, study("detector_langs")),
    addressOnly(data, study("quiet")),
  );
}
