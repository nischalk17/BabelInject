# Report outline (4 pages), working document

Status: outline only. Every number below is already in `results/summary/` and `docs/RESEARCH_LOG.md`; numbers marked
**PENDING** do not exist yet. Nothing goes into the report that is not in `results/` (CLAUDE.md rule). The
owner rewrites the prose in their own words; the structure, the claim list and the caveats are the part to keep.

**Working title:** Do prompt-injection defenses for tool-using LLM agents hold across languages and injection
channels? A small-model study in English, Nepali, Hindi and code-mixed text.

**Page budget:** abstract 0.25 | introduction 0.5 | related work 0.4 | method 1.0 | results 1.3 | discussion and
limitations 0.45 | conclusion and reproducibility 0.1.

---

## 0. Abstract (about 150 words)
Problem (indirect prompt injection against agents, mostly studied in English on large models) -> what we built
(mocked-sandbox benchmark, deterministic judge, 5 languages x 4 channels, 3 attacks, 4 defenses, 3 models) ->
three headline results (language effect and its capability control; defense effects and their costs; model
size is not monotone) -> one-line caveat (small n, one model family). Write last.

## 1. Introduction (0.5 page)
- What an agent is; why tool outputs and documents are an attack surface (use the mailroom analogy only if short).
- The gap: English-only, large hosted models. We ask RQ1 to RQ3 (as in the README).
- Contributions, three bullets: the benchmark (open, reproducible, deterministic judge); the language x channel
  measurements on small open models; the defense comparison with utility cost. State the limits in the last line.

## 2. Related work (0.4 page)
AgentDojo, InjecAgent and BIPIA, plus one sentence each on spotlighting and the sandwich defense.
**Do before writing:** read each abstract and method section and verify author, year and venue; do not cite
from memory. Say how this differs: languages, small local models, deterministic judge, mocked sandbox.

## 3. Method (1.0 page)
- **Sandbox and tasks:** 30 benign tasks (10 facts x email, file, web page); tools incl. `send_email`; the
  body-only fact rule (answers never appear outside the injected item), enforced by tests.
- **Attacks:** `inject_override` (blunt), `inject_owner_note` (authority), `inject_cc_request` (casual, kept as
  a floor control); 5 languages. **Provenance sentence (must stay accurate):** non-English texts were first
  drafted by an AI assistant, then reviewed and corrected line by line by the author, who reads Nepali and Hindi
  (`docs/TRANSLATIONS.md`).
- **Channels:** email, file, web page, tool output (payload appended to the `list_emails` result). Mention the
  channel flaw we found and fixed (the first tool-output definition duplicated the email channel).
- **Judge:** deterministic, from the sandbox action log (an email to the attacker address was sent); never an
  LLM. Utility checked programmatically per task.
- **Models and settings:** `qwen2.5:3b`, `qwen2.5:7b` (Ollama, CPU), hosted `qwen/qwen3.8-27b` (Groq, partial).
  Temperature 0, seed 0, one run per scenario, response cache, model tag logged. Report the non-determinism
  check (actions identical in 10 of 10 repeats; answer wording differed once).
- **Defenses (all v1):** spotlighting, sandwich reminder, tool-permission policy, prompted detector.
- **Statistics:** Wilson 95% intervals; Newcombe intervals for differences (conservative, ignores pairing);
  state that runs share task facts so intervals are somewhat optimistic.
- **Capability control:** the same attack text given as the user's own request.

## 4. Results (1.3 pages; 3 figures, 2 small tables)
| Subsection | Content | Source | Figure or table |
|---|---|---|---|
| 4.1 Language x channel (7B) | en 35/120, mix 12/120, ne 1/120, hi 0/120, ne_rom 0/120; English by channel: file 50%, tool_output 37%, doc 20%, email 10%; item opened 90 to 100% | `table1`, `table4` | Fig 1 (7B heatmap) |
| 4.2 Capability control | 7B follows direct requests 14/15 in every language; hosted 27B follows 1/15 (it refuses, replying in the user's language) | `results/control`, `results/hosted_control` | Table A |
| 4.3 Model size | 3B vs 7B per language; Hindi 10/120 vs 0/120; 3B benign 20/30 vs 29/30 | `table1`, `table3` | Fig 1 (both heatmaps) or Table B |
| 4.4 Defenses (7B, en and mix) | English ASR: none 32/60, spotlight 16, sandwich 6, tool policy 0, detector 0; the detector blocks the task (attacked utility 0/120, benign false positives 4/30) | `table2`, `table2b`, `table3` | Fig 2 and Fig 3 |
| 4.5 Address-only follow-up | **PENDING** (`make run-quiet`, `make run-hosted-quiet`, `make tables-quiet`); predictions are in the research log | `results/summary_quiet/` | one sentence or small table |
| 4.6 Hosted pilot | 0/76 injected on the partial grid; quota stop; not a random slice | `results/hosted` | one sentence |

## 5. Discussion and limitations (0.45 page)
**Claims we can make:** the attack and defense numbers above for these models and settings; near-zero non-English
ASR on 7B is not a comprehension failure (control); defenses differ sharply in cost; ASR is not monotone in size.

**Claims we cannot make:** that Nepali or Hindi are "safer"; anything about large frontier models; any defense
result outside English and code-mixed (not run elsewhere); why the 27B refuses or why the 3B is vulnerable in
Hindi (untested).

**Limitations to state (each is already logged):** one model family; single run per scenario; n=10 to 60 per
cell; tool policy is 0% by construction and no benign task needs `send_email`; the detector blocks tool results;
the capability control has n=3 per language; the hosted data is partial and the attacker address may itself
trigger refusals; the 3B often never reads the injected item; hosted models can change silently.

**Future work:** less conspicuous attacks and wording, larger and non-Qwen models, defenses in non-English
languages, a multilingual detector.

## 6. Conclusion and reproducibility (0.1 page)
Two sentences of findings. Reproduce: `make setup`, `make run-all`, `make figures`; every figure has a CSV twin;
config files define every experiment; raw rows are not committed, summary CSVs are. Ethics: fictional data, mocked
sandbox. Repository link and tag `v1.0`.

---

## Figures and tables to include
1. Fig 1: ASR heatmaps by language x channel (`docs/figures/fig1_asr_heatmap_*.png`; 7B in the body, 3B in the same figure or an appendix).
2. Fig 2: defense effect on ASR and utility (`fig2_defense_effect_*.png`).
3. Fig 3: ASR vs utility trade-off (`fig3_tradeoff_*.png`).
4. Table A: capability control (7B and hosted). Table B: 3B vs 7B per language.

## Writing order and ownership
1. Method and results (me, from `results/`, first draft). 2. Discussion and limitations (me, from the log).
3. Introduction, abstract, conclusion (you, in your own words; I check the numbers). 4. Related work (after you
skim the three papers). 5. Final numbers check: every figure in the text compared against `results/summary/`.
