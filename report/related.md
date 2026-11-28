# 2. Related work

**Status:** checked against the papers' full text (arXiv HTML versions) and their publisher pages on 2026-11-28.
Every claim below was read in the text; the per-claim evidence, the corrections made to the earlier draft and
what could not be checked are in `report/related_verification.md`.

**Indirect prompt injection.** Greshake et al. [1] introduced *indirect* prompt injection: instructions hidden
in data that an LLM-integrated application retrieves, so the attacker needs no direct access to the model. Three
benchmarks measure it. BIPIA [2] covers five application scenarios (email, web page and table question
answering, summarization and code question answering) and 250 attacker goals (30 text and 20 code attack types,
five instructions each), evaluates 25 LLMs, and finds a positive association between a model's capability
and its attack success on text attacks but none on code attacks. Its tasks are prompt-level, not tool-calling,
and success is computed by a pipeline that combines rules, an LLM judge and language detection. InjecAgent [3]
targets tool-integrated agents with 1,054 test cases, each pairing one of 17 user cases with one of 62 attacker
cases (30 direct-harm and 32 data-stealing), placed in static, simulated tool responses; it evaluates 30 agents
and judges success by rule on the parsed tool call. A ReAct-prompted GPT-4 agent had 24% attack success, rising
to 47% when a "hacking prompt" was added. AgentDojo [4] is a stateful, extensible environment with four suites
(workspace, Slack, travel, banking), 97 user tasks and 629 security test cases over dummy data. Its utility and
security checks are deterministic code over the environment state, not an LLM judge, and it reports benign
utility, utility under attack and targeted attack success. It reports that more capable models tend to be easier
to attack and that injections near the end of a tool response work best.

**Defenses.** AgentDojo compares four defense families that we also test: data delimiters (following spotlighting
[5]), a prompt-injection detector, repeating the user's prompt after each tool call (a sandwich), and a tool
filter. It reports that a secondary detector brings attack success down to 8% but, because of false positives,
"significantly degrades utility", and that a tool filter fails when the tools a task needs are also sufficient
for the attack. BIPIA proposes black-box defenses (an explicit reminder, a multi-turn dialogue format and
in-context examples) and a white-box defense that fine-tunes with special data tokens and adversarial training.
Spotlighting [5] marks untrusted text by delimiting, datamarking or encoding it; with GPT-family models it
reports attack success falling from above 50% to below 2%. The strongest numbers come from datamarking and
encoding: the paper reports that delimiting alone roughly halves attack success and says its authors do not
recommend delimiting in practice. Our spotlighting defense is the delimiting form.

**Language and model safety.** Work on language and safety studies *direct* harmful requests, not injection or
agents. Deng et al. [6] translate unsafe prompts into other languages and find that low-resource languages are
about three times as likely as high-resource ones to elicit harmful content from ChatGPT and GPT-4 when the user
does not intend a jailbreak, and that combining a jailbreak with translation gives 80.92% unsafe output for
ChatGPT and 40.71% for GPT-4. Yong et al. [7] report that translating AdvBench prompts into low-resource
languages (Zulu, Scots Gaelic, Hmong, Guarani) gets GPT-4 to engage with 79% of them, against under 1% in English;
Hindi, which they class as high-resource, reaches 6.5% and Bengali 13.3%. Neither study includes Nepali, and
neither uses a tool-using agent.

**What this work adds, and what it does not.** Across the benchmark papers we read, we found no comparison of the
same attack across languages. We add (i) the same three attacks in five languages (English, Nepali, romanized
Nepali, Hindi and code-mixed text) across four channels, with a capability control that separates "cannot
follow the language" from "does not act on injected text"; (ii) small local models (3B, 7B) plus one hosted
model, instead of frontier models; and (iii) a comparison of four defense families on one grid with their cost in
benign utility. The language studies [6, 7] point the other way for direct requests (more unsafe output in
low-resource languages), but they use a different threat model and much larger models, so the results are not
comparable. Deterministic judging is not new: AgentDojo and InjecAgent also judge from actions and state. Our
benchmark is smaller (30 benign tasks, 3 attack templates), our defenses are simple versions, and we do not claim
to reproduce or beat any cited result.

**Table 1. Comparison with the three benchmarks** (from the papers' own descriptions).

| | BIPIA [2] | InjecAgent [3] | AgentDojo [4] | BabelInject (this work) |
|---|---|---|---|---|
| Setting | prompt-level QA, summarization, code QA | tool-integrated agent, static simulated tool replies | stateful tool environment, dummy data | mocked sandbox, ReAct tool loop, 7 tools |
| Size | 5 scenarios, 250 attacker goals | 1,054 test cases | 97 tasks, 629 security cases | 30 benign tasks, 3 attacks x 5 languages x 4 channels |
| Success judged by | rules, LLM judge, language detection | rule on the parsed tool call | deterministic state checks | deterministic check of the outbox |
| Models | 25 LLMs | 30 agents | several LLMs (see the paper) | Qwen 3B, 7B (local), 27B (hosted) |
| Defenses evaluated | 3 black-box, 1 white-box | none | delimiters, detector, sandwich, tool filter | delimiting, sandwich, tool policy, detector |
| Cross-language analysis | none found | none found | none found | five languages, capability control |
