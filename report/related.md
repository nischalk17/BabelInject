# 2. Related work (first draft, about 0.4 page)

Status: draft. Authors, years, venues and headline claims were checked on 2026-11-23 against the arXiv,
NeurIPS and ACL pages (abstract level, from search results). The owner should still skim each paper's
abstract, threat model and metric definitions before submitting, and confirm anything quoted below.
Do not add claims about these papers that are not in this list.

Indirect prompt injection, where an attacker's instructions arrive inside content an agent retrieves rather
than from the user, is studied in several benchmarks. BIPIA (Yi et al., arXiv:2312.14197, KDD 2025) covers
five application scenarios and 250 attacker goals, evaluates 25 models, reports that more capable models had
higher attack success, and proposes boundary-awareness and explicit-reminder defenses. InjecAgent (Zhan et
al., ACL Findings 2024, arXiv:2403.02691) offers 1,054 test cases over 17 user tools and 62 attacker tools for
tool-integrated agents and evaluates 30 agents; a GPT-4 agent reached 24% attack success, 47% with an added
"hacking prompt". AgentDojo (Debenedetti et al., NeurIPS 2024 Datasets and Benchmarks, arXiv:2406.13352)
provides an extensible, stateful environment with 97 tasks and 629 security test cases; it reports attacks
succeeding in under 25% of cases against the best agents, and a secondary detector lowering this to 8%.
Spotlighting (Hines et al., arXiv:2403.14720) marks untrusted input by delimiting, datamarking or encoding it,
and reports lowering attack success from over 50% to under 2% on GPT-family models.

Our work differs in four ways. First, language: these works, as far as their abstracts state, evaluate
English, whereas we compare English, Nepali, romanized Nepali, Hindi and code-mixed text, with a capability
control that separates "cannot follow the language" from "does not act on injected text". Second, models: we
study small open models (3B, 7B) run locally, plus one hosted model, rather than frontier models. Third,
judging: success is decided deterministically from a mocked sandbox's action log, never by an LLM. Fourth,
scale: our benchmark is smaller (30 benign tasks, 3 attack templates) and our defenses (a delimiting form of
spotlighting, a task-reminder "sandwich", a tool policy, a prompted detector) are simple versions, so we do
not claim to reproduce or beat the cited results.
