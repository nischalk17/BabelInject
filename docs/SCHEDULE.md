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
- **Done Nov 23:** full no-defense grid on 7B (630 runs); tables and heatmap built and logged. Non-English
  attacks are about 0% on 7B; the capability control (done) shows it is not a comprehension limit.

## Revised plan

| Day | Claude | You | Compute |
|---|---|---|---|
| **Nov 23 (Mon)** | Check the full grid finished; `uv sync`; `make figures`; log the real language x channel table. Decide the defense-grid languages. Build the **language-capability control** (done). Put the first real table in the README | Commit and push; (control needed no new translations); skim AgentDojo and InjecAgent; tag `v0.1-mvp` after the README table is in | After the grid: capability control (small), then the defense grid on 7B (about 4 h) |
| **Nov 24 (Tue)** | Hosted Groq run (`qwen/qwen3.8-27b`, all languages); 3B no-defense grid; figures for defenses; start the report | Send professor emails with the repo link once the README has the first table | 3B grid (about 2 h) and hosted run (rate-limited) overnight |
| **Nov 25 (Wed)** | Final tables and figures from `results/`; 4-page report draft; clean-clone reproduction of one table | Edit the report in your own words (method, translations, limitations) | none, or reruns of any failed run |
| **Nov 26 (Thu), end** | Polish docs; final numbers check against `results/` | Final read; commit; tag `v1.0` | none |

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
| Defense grid, 7B (5 defenses; the detector adds one call per tool result) | 750 (150 of them cached) | about 4 h |
| No-defense grid, 3B | 630 | about 2 h |
| Hosted Qwen 27B, no defense | up to 630 | depends on rate limits |

## If we fall behind, cut in this order
1. Defenses on fewer languages.
2. Doc and file channels for English and Nepali only on the secondary models.
3. Hosted run on a subset of cells.

**Never cut:** the deterministic judge, per-run logging, and reporting n with confidence intervals.
