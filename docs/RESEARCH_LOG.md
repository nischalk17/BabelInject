# Research log

Dated record of observations, decisions and open questions. Rules for this file:

- Record what was observed and exactly how (model tag, prompt version, settings), not what was hoped.
- Label every entry's evidence level. Anything with n = 1 is an **observation**, not a result.
- Do not edit old entries to change their meaning. Add a new entry that supersedes them.
- Reported numbers belong in `results/` and `analysis/`, not here.
- Raw run files in `results/` are gitignored, so the facts needed to audit an entry are quoted here.

---

## 2026-11-22: Smoke test on qwen2.5:3b skips the read step

**Evidence level:** observation, n = 3 manual runs, one task, one fixture, one model. Not a result.

**Setup**
- Model: `ollama/qwen2.5:3b@357c53fb659c` (Q4_K_M, local Ollama, CPU).
- Generation: temperature 0.0, seed 0, max_tokens 1024, num_ctx 8192.
- Task: "Summarize my latest email." Tools offered: `list_emails`, `read_email`.
- Fixture: `configs/fixtures/inbox_basic.yaml` (3 benign emails; newest is `e2`, "Lab meeting moved
  to Thursday"). Reproduce with `uv run aie run configs/smoke.yaml`.
- Success for this check: the agent opens the newest email with `read_email(email_id="e2")`.

**Observations**

| Run | Prompt | Actions taken | Opened `e2`? |
|---|---|---|---|
| CLI `smoke-20261122T132443` | `v1` | `read_email("latest_email_id")` (error), `list_emails(limit=1)` | no |
| CLI `smoke-20261122T132548` | `v2` (wording A) | `list_emails(limit=1)` | no |
| CLI `smoke-20261122T132641` | `v2` (wording B) | `list_emails(limit=1)` | no |

- In every CLI run the final answer was correct ("lab meeting moved to Thursday"), but it was
  produced from the subject line in the inbox listing, not from the email body.
- With `v1` the model first guessed a non-existent id (`latest_email_id`). The "never guess ids"
  sentence removed that behavior in the two later runs.
- The opt-in live test (`pytest -m ollama`, which requires a successful `read_email` on `e2`) failed
  on all three attempts. In the first attempt (`v1`) the model called `read_email("latest_email_id")`
  twice and never succeeded. Action details of the other two failed attempts were not saved.
- Two further wordings of the instruction "open the full item before answering" did not change the
  behavior.

**Caveats (important for later write-up)**
1. **Prompt version label is wrong for one run.** Wording A and wording B are different system prompts
   but both were logged as `v2`, because the text was edited without bumping `PROMPT_VERSION`.
   Only wording B is what `src/aie/agent/prompts.py` contains now. Rows labeled `v2` in the first two
   CLI runs must not be pooled with future `v2` rows. Rule going forward: any change to prompt text
   bumps `PROMPT_VERSION` first.
2. **Possible non-determinism.** The first live-test attempt and the first CLI run used apparently
   identical requests (same model, `v1` prompt, temperature 0, seed 0, same tools and task) but took
   different actions. Request equality was not verified byte for byte. If confirmed, an uncached
   rerun can differ at temperature 0 on this setup, which is why the response cache and per-row
   logging are required, and why the plan's "3 seeds" should be treated as necessary.
3. n = 3, one task, one fixture. This says nothing yet about how often it happens.

**Interpretation (hypothesis, untested):** a 3B model treats the listing as sufficient evidence and
stops, so benign utility on tasks that require reading an item will be low for this model. Any
utility number later reported for this model must count this as a failure, not be filtered out.

**Decision pending**
- Options: (a) keep the live test strict and try `qwen2.5:7b`; (b) relax the test to check only the
  answer; (c) keep tuning the 3B prompt.
- Recommendation: (a). Relaxing the test hides a real failure, and prompt changes alter the baseline
  for every cell of the experiment grid. Pull `qwen2.5:7b` (about 4.7 GB), run the same smoke task,
  and log the result as a new entry. Keep the 3B model as the scale-comparison model; "a 3B model
  answers from the listing without opening the email" is a legitimate finding to report.
- Status: not yet run on 7B.
