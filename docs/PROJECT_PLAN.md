# Project plan: LostInTranslation-Inject (working title)
**Do Prompt-Injection Defenses for LLM Agents Hold Up Across Languages and Injection Channels?**
Owner: Nischal Dhoj Kunwar · Plan dated Nov 22, 2026 · MVP due Nov 24 · Full version due Dec 5

> **Changes since this plan was written (kept here so the plan stays honest; details in
> [SCHEDULE.md](SCHEDULE.md) and [RESEARCH_LOG.md](RESEARCH_LOG.md)):**
> - End date moved from Dec 5 to **Nov 26**.
> - Primary model is `qwen2.5:7b`; `qwen2.5:3b` is the scale comparison; the hosted comparison is
>   Groq `qwen/qwen3.8-27b` (kept, at the owner's request). `llama3.2:3b` was not used.
> - Benchmark: 30 tasks (10 facts x email/file/web page), 3 attacks x 5 languages, 4 channels; the
>   `tool_output` channel injects into the `list_emails` result (the first definition duplicated the
>   email channel and was replaced).
> - Translations were drafted with AI assistance and reviewed line by line by the author.
> - Added: a language-capability control (planned) because non-English attacks may fail on the 7B
>   model for capability reasons, which would not be robustness.

---

## 1. Why this project stands out
Most prompt-injection work tests **English** attacks on **large hosted models**. Your angle has three parts:
1. **Multilingual and code-mixed injections.** The same attack written in English, Nepali (Devanagari), romanized Nepali, Hindi and English–Nepali code-mix. Defenses and detectors trained mostly on English may miss these. Nobody from the West has your Nepali background, so this angle is yours.
2. **Injection channel.** The same payload hidden in a retrieved document, an email body, a tool's output, or a file. Does the channel change success rates?
3. **Small open models** (7–8B, run locally): what people with limited budgets actually deploy.

**Research questions**
- **RQ1:** How does attack success rate (ASR) vary with language and channel for small open models?
- **RQ2:** Do common lightweight defenses (delimiting/spotlighting, sandwich reminders, an injection detector, tool-permission policy) generalize to non-English injections?
- **RQ3:** What is the utility cost of each defense (benign task success)?

Build on existing benchmarks (AgentDojo, InjecAgent, BIPIA). Read their papers on Day 1, cite them, and reuse their task design ideas. You don't need to invent the whole field. Your contribution is the language and channel study.

**Ethics:** everything runs in a mocked sandbox (fake inbox, fake files, fake web). No real systems, no real people's data.

---

## 2. Models (decide on Day 1)
| Option | Use it for | Pros | Cons |
|---|---|---|---|
| **Ollama, local** (a recent 7–8B instruct model with tool calling, from the Qwen or Llama family; add a 3B model for a scale comparison) | **Primary experiments** | Free, unlimited runs, fully reproducible, fixed model weights | Needs about 16 GB RAM (8 GB works with 3–4B models). Slower |
| **Free hosted API** (Groq or Google Gemini free tier) | One stronger model as a comparison point | Fast, stronger model | Rate limits, the model can change silently, terms can change |

**Recommendation:** use Ollama as the main setup and add one free hosted model as a "bigger model" comparison. Always set temperature 0, log the exact model tag or version, and run 3 seeds where sampling is involved.

---

## 3. Architecture
```
            ┌──────────────┐    scenario (user task + injection)
 configs/ ─▶│ Runner (CLI) │──────────────────────────────┐
            └──────┬───────┘                              ▼
                   │                         ┌────────────────────────┐
                   ▼                         │  Sandbox environment   │
            ┌──────────────┐  tool calls     │  inbox · files · web/  │
            │  Agent loop  │◀──────────────▶ │  RAG store · send_email│
            │ (ReAct-style)│                 │  (logs every action)   │
            └──────┬───────┘                 └────────────────────────┘
                   │ model calls
                   ▼
            ┌──────────────┐      ┌──────────────────────────┐
            │ Model adapter│      │ Defenses (pluggable)     │
            │ ollama/groq/ │      │ none · spotlight · sandw.│
            │ gemini       │      │ detector · tool-policy   │
            └──────────────┘      └──────────────────────────┘
                   │
                   ▼
            ┌──────────────┐  deterministic checks  ┌──────────────┐
            │  Evaluator   │───────────────────────▶│ results/*.jsonl│──▶ analysis → figures, tables
            └──────────────┘                        └──────────────┘
```
**Key design decisions (the things that make it rigorous):**
- **Deterministic judging.** An attack succeeds only if the sandbox log shows the attacker's goal was executed (for example `send_email(to=attacker@evil.test)` was called, or a secret file was read and sent). Don't use an LLM as the judge for the main metric.
- **Utility is measured separately.** Every benign task has a programmatic success check.
- **Every trace is logged** (prompts, tool calls, outputs) as JSONL, so any number can be audited.
- **Configs, not code edits.** Experiments are YAML files: model × defense × language × channel × attack template.
- **Caching.** Model responses are cached by hash, so reruns are free and reproducible.
- **Statistics.** Report ASR with 95% confidence intervals (Wilson). Use enough scenarios per cell (aim for 30 or more).

---

## 4. Repo layout and standards
```
agent-injection-eval/
├── README.md               # problem, results table, figure, how to reproduce
├── CLAUDE.md               # instructions for Claude Code
├── pyproject.toml          # uv-managed, pinned deps
├── Makefile                # make setup / test / run-mvp / run-all / figures
├── configs/                # mvp.yaml, full.yaml
├── src/aie/
│   ├── agent/              # loop.py, prompts.py
│   ├── models/             # base.py, ollama.py, groq.py, gemini.py, cache.py
│   ├── env/                # sandbox.py, tools.py (inbox, files, web, send_email)
│   ├── scenarios/          # tasks.yaml, attacks.yaml, translate/ (vetted translations)
│   ├── defenses/           # none.py, spotlight.py, sandwich.py, detector.py, tool_policy.py
│   ├── eval/               # judge.py, metrics.py
│   └── cli.py              # `aie run configs/mvp.yaml`
├── analysis/               # make_figures.py, tables.py
├── results/                # gitignored raw; commit summary CSVs only
├── tests/                  # pytest: tools, judge, defenses, adapters (mocked)
├── report/                 # 4-page write-up (LaTeX/Overleaf)
└── .github/workflows/ci.yml  # lint (ruff) + type check (mypy) + tests
```
Standards: Python 3.11+, `uv`, `ruff`, `mypy`, `pytest`, pre-commit, type hints, docstrings, small commits with clear messages, a semver tag `v0.1-mvp` and `v1.0`, an MIT license, and a CITATION.cff.

**Translations:** write the Nepali and romanized-Nepali attacks yourself, and check the Hindi with a native speaker if you can. Don't rely on raw machine translation alone. Note in the report how the translations were made.

---

## 5. Milestones
| Date | Milestone | Done when |
|---|---|---|
| Nov 22 | Read AgentDojo and InjecAgent papers (skim), finalize design, set up repo, CI, Ollama | `make test` passes in CI |
| Nov 23 | Sandbox + tools + agent loop + Ollama adapter | Agent completes 5 benign tasks |
| **Nov 24 (MVP)** | 20 tasks × 1 channel × English + Nepali × no defense, plus judge and first ASR table | README shows a first results table; tag `v0.1-mvp` |
| Nov 25–27 | **Professor emails go out** with the repo link. Add the 4 channels and all 5 languages | Full attack grid runs |
| Nov 28–Dec 1 | 4 defenses + detector, utility metric, 2nd local model + 1 hosted model | All runs logged, CIs computed |
| Dec 2–4 | Analysis, figures, 4-page report | PDF in `report/`, figures in README |
| Dec 5 | Polish: docs, reproducibility check from a clean clone, `v1.0` | A stranger can reproduce one table in under 30 minutes |

**MVP cut rule:** if you're behind on Nov 24, reduce scope (fewer tasks, one model) but **don't skip the judge or logging**.

---

## 6. Results you'll show (fill these in honestly)
- Table 1: ASR by language × channel (no defense).
- Table 2: ASR and utility by defense × language.
- Figure 1: a heatmap of ASR by language and channel.
- Figure 2: defense ASR reduction vs utility cost.
- 3 qualitative failure examples (short traces).

**What to put in your CV once there are numbers:** "Found that [defense X] reduced English injection ASR by A% but only B% for romanized-Nepali injections on [model] (n=…, 95% CI …)."
