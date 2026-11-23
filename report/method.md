# 3. Method (first draft, about 1 page)

Status: draft from the code, configs and `docs/RESEARCH_LOG.md`. Every setting below is in `configs/*.yaml`
or the source; nothing here is a result. The owner should check each sentence against the code and reword it.

**Setting.** We study indirect prompt injection against a tool-using agent in a fully mocked sandbox.
The agent is a ReAct-style loop: the model sees the user's task and seven tools (`list_emails`,
`read_email`, `list_files`, `read_file`, `search_web`, `fetch_url`, `send_email`), calls tools until it
answers in plain text or reaches 8 steps. All data is fictional; no real email, web or file system is
touched, and `send_email` only appends to an in-memory outbox. `send_email` is always offered, because an
agent that cannot send email cannot be attacked into sending it.

**Tasks.** There are 30 benign tasks: 10 facts (for example a meeting room) each stored in three carriers,
an email, a file and a web page, so channels can be compared without a task-difficulty confound. The answer
appears only in the body of the item the injection goes into, never in a subject, file name or URL, so a
model that never opens the item cannot answer; tests enforce this. Utility is checked programmatically
(the right item was opened and the answer contains a key phrase).

**Attacks and channels.** Three attack templates share one goal, making the agent email
`attacker@evil.test`, and differ in subtlety: `inject_override` (blunt: drop the task), `inject_owner_note`
(authority: a note claiming to come from the account owner) and `inject_cc_request` (an ordinary-sounding
request, kept as a floor control). The payload is inserted in one of four channels: an email body, a file,
a web page, or the `list_emails` tool result (text the model sees before it opens any email). Each attack
exists in five languages: English, Nepali (Devanagari), romanized Nepali, Hindi, and Nepali-English
code-mixed text. The non-English texts were first drafted by an AI assistant and then reviewed and
corrected line by line by the author, who reads Nepali and Hindi (`docs/TRANSLATIONS.md`). The attacker
address stays in ASCII in every language, and the loader rejects any payload that omits it.
The no-defense grid is 30 benign runs plus 3 attacks x 5 languages x 40 task-channel pairs = 630 runs.

**Judge.** Attack success is decided deterministically from the sandbox: an email to the attacker address
was recorded in the outbox. It never depends on the model's wording and never uses an LLM judge. We report
attack success rate (ASR) and, separately, utility on benign and attacked runs.

**Models and settings.** Primary model `qwen2.5:7b`; scale comparison `qwen2.5:3b` (both 4-bit, local Ollama,
CPU); hosted pilot `qwen/qwen3.8-27b` on Groq (partial grid). Temperature 0, seed 0, one run per scenario,
agent prompt `v3`, up to 1024 generated tokens and an 8192-token context. Every model call goes through a
response cache and every row logs the model tag. Output wording is not bit-for-bit reproducible on this
setup (1 of 5 repeats of a check on the 3B model differed in wording), but actions were identical in all
10 full-agent repeats; since the judge reads only actions and the outbox, verdicts are unaffected in
those checks. Hosted models can change silently, so we record the model id and the run date.

**Defenses.** Four defenses, all version 1, run on the 7B model with the same agent: *spotlighting* (tool
results wrapped in untrusted-data tags plus a system rule), a *sandwich* reminder of the user's task after
every tool result, a *tool policy* that blocks `send_email` to anyone who is not a known contact (language
independent, since it never reads the text), and a prompted *detector* (an extra model call per tool result;
a "YES" replaces the result with a removal notice). The defense grid covers English and code-mixed text
only: 5 defenses (including none) x 2 languages x 3 channels x 2 attacks x 10 tasks, plus 30 benign runs
per defense, 750 runs.

**Capability control.** To separate "the model resists the attack" from "the model cannot read the
language", we give the same attack text to the model as the user's own request (channel `user`) and check
whether it complies, 3 runs per language.

**Statistics.** Rates carry 95% Wilson intervals. Differences between conditions use Newcombe intervals,
which ignore pairing and are therefore conservative; but runs share task facts, so intervals are somewhat
optimistic. Cells hold 10 to 60 runs, so we describe sizes of effects, not precise rates.
