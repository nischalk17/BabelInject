# Schedule: finish Nov 26

Set on Nov 22, 2026; updated the same evening. The original plan ended Dec 5; the owner chose **Nov 26**
and to keep the hosted-model comparison. **There is no slack:** a failed overnight run or a late
decision moves the end to Nov 27.

Legend: **Claude** = code, analysis, drafts. **You** = review, decisions, git commits and tags.

## Done by the evening of Nov 22 (about a day ahead of the first schedule)
- Infrastructure: models, cache, sandbox, agent loop, judge, grid runner, statistics.
- Benchmark content: 30 tasks, 3 attacks x 5 languages (translations AI-drafted, author-reviewed),
  4 channels. Two design flaws found and fixed (no send tool; duplicated tool-output channel).
- English calibration on 7B (see `RESEARCH_LOG.md`).
- Groq hosted adapter, tested live. Four defenses with tests. Analysis tables and figures with tests.
- **Done Nov 23:** 3B no-defense grid (630 runs) read and logged. 7B defense grid (750 runs, English + code-mixed), logged. Full no-defense grid on 7B (630 runs); tables and heatmap built and logged. Non-English
  attacks are about 0% on 7B; the capability control (done) shows it is not a comprehension limit.

## Revised plan (updated Nov 23, evening)

| Day | Claude | You | Compute |
|---|---|---|---|
| **Nov 23 (Mon)** | Done: full 7B grid, tables, capability control, 7B defense grid, hosted pilot (quota stop), 3B grid (done) | Commit and push; skim AgentDojo and InjecAgent; tag `v0.1-mvp` | none |
| **Nov 24 (Tue)** | `make run-quiet` done (7B, logged); after about 09:30, `make run-hosted-quiet` (about one day of free quota); write the report (outline done in `report/OUTLINE.md`; method and results first, from `results/`) | Send professor emails with the repo link (README already has results); review the report draft | Optional: resume the hosted run when the daily token window reopens (about 87 runs per day; the quota refills continuously, about 8,300 tokens an hour) |
| **Nov 25 (Wed)** | Final tables and figures; finish the report; clean-clone reproduction of one table; doc audit | Edit the report in your own words (method, translations, limitations) | none, or reruns of failures |
| **Nov 26 (Thu), end** | Final numbers check against `results/` | Final read; commit; tag `v1.0` | none |

## Decisions still open
1. **Defense-grid languages.** Decided Nov 23: English and code-mixed on 7B (`configs/defenses.yaml`, channels file, doc, tool_output). The full grid confirmed that Nepali, romanized Nepali and Hindi attacks
   barely work on 7B (0 of 120 each), so defenses have nothing to reduce there. The hosted 27B model covers all languages.
2. **Capability control.** Done: 14/15 direct requests followed in all languages, so the 0% injected ASR is not a comprehension limit (n=3 per language).

## Compute estimates (measured, not guessed)
About 20 to 35 s per uncached 7B run when nothing else is using the CPU; repeated requests are served from
the response cache. My own test and figure runs slow a running grid, so nothing else should run during one.

| Run | Runs | Est. time |
|---|---|---|
| Full no-defense grid, 7B | 630 | 4 to 5 h (running) |
| Defense grid, 7B (5 defenses; the detector adds one call per tool result) | 750 | done, about 3 h |
| No-defense grid, 3B | 630 | about 2 h |
| Defenses on 3B, Hindi + English (`make run-defenses-3b-hi`; 80 runs cached) | 400 | about 1 to 1.5 h (estimate, not yet measured) |
| Hosted Qwen 27B: control + no-defense subset (file, tool_output) | 245 | **hit the free-tier cap of 200,000 tokens/day after 102 runs** (control done, grid 87 of 230); finishing it needs about 1.5 more days of quota |

## If we fall behind, cut in this order
1. Defenses on fewer languages.
2. Doc and file channels for English and Nepali only on the secondary models.
3. Hosted run on a subset of cells.

**Never cut:** the deterministic judge, per-run logging, and reporting n with confidence intervals.
