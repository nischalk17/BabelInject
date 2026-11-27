// Sanity checks on a finished build: base path, data files present and consistent, nothing private.
// Usage: node scripts/check-dist.mjs [distDir]
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const dist = resolve(process.argv[2] ?? "dist");
const base = "/BabelInject/";
const problems = [];
const read = (rel) => readFileSync(join(dist, rel), "utf-8");
const json = (rel) => {
  try {
    return JSON.parse(read(rel));
  } catch (error) {
    problems.push(`${rel}: ${error.message}`);
    return null;
  }
};

const html = read("index.html");
if (!html.includes(`${base}assets/`)) problems.push(`index.html does not load assets from ${base}assets/`);
if (/(src|href)="\/assets\//.test(html)) problems.push("index.html has an asset URL without the base path");

const summary = json("data/summary.json");
const meta = json("data/meta.json");
const index = json("data/traces/index.json");
if (summary && meta && summary.schema_version !== meta.schema_version) {
  problems.push("summary.json and meta.json disagree on schema_version");
}
if (summary && !summary.studies?.some((s) => s.status === "ok")) problems.push("summary.json has no study with data");
for (const entry of index?.traces ?? []) {
  const trace = json(`data/traces/${entry.id}.json`);
  if (trace && trace.id !== entry.id) problems.push(`trace ${entry.id}: id mismatch`);
}
if (!index?.traces?.length) problems.push("traces/index.json lists no traces");

// Nothing private may ship: keys, absolute home paths, personal email addresses, raw result rows.
const forbidden = [
  [/gsk_[A-Za-z0-9]{10,}/, "an API key"],
  [/GROQ_API_KEY/, "the API key variable name"],
  [/[A-Za-z]:\\{1,2}Users/, "a Windows home path"],
  [/@gmail\.com/, "a personal email address"],
];
const walk = (dir) =>
  readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
for (const file of walk(dist)) {
  if (file.endsWith(".jsonl")) problems.push(`${file}: raw result rows must not be published`);
  if (!/\.(html|js|css|json|svg|txt|map)$/.test(file)) continue;
  const text = readFileSync(file, "utf-8");
  for (const [pattern, what] of forbidden) {
    if (pattern.test(text)) problems.push(`${file}: contains ${what}`);
  }
}

if (problems.length) {
  console.error(problems.map((p) => `- ${p}`).join("\n"));
  process.exit(1);
}
console.log(`dist ok: ${index.traces.length} traces, base ${base}`);
