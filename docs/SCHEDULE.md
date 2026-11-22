# Schedule: finish Nov 26

Set on Nov 22, 2026. The original plan ended Dec 5; the owner chose Nov 26 and to keep the hosted-model
comparison. **There is no slack.** If an overnight run fails or a translation slips a day, the end
moves to Nov 27.

Legend: **Claude** = code, drafts, analysis. **You** = review, decisions, git commits and tags.

| Day | Claude | You | Overnight run (laptop on power, sleep off) |
|---|---|---|---|
| **Nov 22 (Sun)** | Wrote `docs/EXPLAINED.md`, this schedule, the reading guide | Commit and push. Read EXPLAINED.md once | none |
| **Nov 23 (Mon)** | 3 English attacks of different subtlety; grow to 10 tasks (body-only facts; some with file or web injection points); calibrate ASR on 7B (aim: not about 0% and not about 100% on English); draft ne, ne_rom, hi, mix payloads in `docs/TRANSLATIONS.md`; start the Groq adapter | Skim AgentDojo and InjecAgent (about 1 h each); create a free Groq account and API key; review the **Nepali** lines | MVP grid: English + Nepali, email + tool_output |
| **Nov 24 (Tue), MVP** | Put reviewed Nepali into `attacks.yaml`; first ASR table in README from `results/` only | Review the other languages by tonight; commit; `git tag -a v0.1-mvp -m "MVP: first ASR table"`, then `git push origin v0.1-mvp` | Full no-defense grid on 7B: 10 tasks x 3 attacks x 5 languages x 4 channels = 600 runs |
| **Nov 25 (Wed)** | Four defenses (spotlight, sandwich, tool policy, detector) with tests; `analysis/`; hosted-model run | Send professor emails with the repo link (after the MVP table is in the README) | Defense grid on 7B (4 x 3 languages x 2 channels x 20 = 480 runs) + 3B no-defense grid |
| **Nov 26 (Thu), end** | Tables and figures from `results/`; 4-page report draft; clean-clone reproduction of one table | Edit the report in your own words; commit; tag `v1.0` | none |

## Compute estimates
These are rough, from about 20 to 40 s per 7B run measured on a handful of runs. They will be
re-measured on Nov 23.

| Run | Runs | Est. time |
|---|---|---|
| MVP grid (7B) | about 40 | under 30 min |
| No-defense grid (7B) | 600 | about 4 to 5 h |
| Defense grid (7B) | 480 | about 4 h |
| No-defense grid (3B) | 600 | about 2 h |
| Hosted model | up to 600 | depends on rate limits |

## If we fall behind, cut in this order
1. Defenses on 2 languages instead of 3.
2. Doc and file channels for English and Nepali only.
3. Hosted run on the no-defense grid only.

**Never cut:** the deterministic judge, per-run logging, and reporting n with confidence intervals.
