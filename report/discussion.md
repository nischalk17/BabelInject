# 5. Discussion and limitations (first draft, about 0.45 page)

Status: draft (updated after the detector probe) from `docs/RESEARCH_LOG.md` and `results.md`. The hosted quiet run is included.

**What the results support.** For these models and settings, indirect injection against a tool-using agent
works in English and code-mixed text, depends strongly on where the text appears, and barely works in Nepali,
romanized Nepali or Hindi on the 7B model. The capability control shows this is not because the 7B cannot
follow those languages: it followed direct requests in 14 of 15 runs. Defenses differ sharply in cost:
sandwich cut English attack success from 32/60 to 6/60 with no benign utility loss (30/30), while the
detector reached 0% only by withholding tool results, so every attacked task failed. Attack success is
not monotone in model size: the 3B was more exposed in Hindi (10/120) than the 7B (0/120).

**What they do not support.** We cannot say Nepali or Hindi are "safer": zero success on one small model, for
three author-reviewed attack texts, is a floor result: it leaves no room to measure a defense, and the
capability control rules out only an inability to follow the language, not other explanations. We cannot say anything about large frontier models; the only larger
model is a partial hosted pilot (0/76), and we do not know why it refuses direct requests (a plainer attacker address did not change this: 1/100 injected runs). We saw one defense language gap, on the 3B (the detector flags Hindi attacks about half as often as English ones; n = 40 per cell), and none on the 7B. We cannot say defenses in general work in Nepali, Hindi or romanized Nepali: only the detector was run
there (it flagged all 20 of 20 runs per cell, and flagged 0 of 6 harmless Nepali, romanized Nepali and Hindi sentences); spotlighting, sandwich and
tool policy were not. We do not know why the 3B is
vulnerable in Hindi.

**Limitations.**
- One model family (Qwen 2.5, plus one hosted Qwen); one run per scenario at temperature 0; cells hold 10 to
  60 runs, so intervals are wide, and runs share task facts, so they are somewhat optimistic.
- Three attack templates, written for this study; non-English texts were AI-drafted and author-reviewed. A
  different wording could change the rates, and we did not test wording.
- Tool policy reaches 0% by construction (no benign task needs `send_email`), so it is a ceiling, not a
  measured defense. The detector and sandwich prompts are in English.
- The capability control has only 3 runs per language, and the 3B often never reads the injected item, which
  limits what its rates mean.
- The hosted grid is partial (87 of 230 runs; the free-tier token quota stopped it); the hosted quiet run (100 runs) is complete and hosted models can change silently.
- The sandbox is mocked and the goal is one action (sending an email); real deployments differ.

**Future work.** Less conspicuous attacks and varied wording; larger and non-Qwen models; defenses tested in
non-English languages; a multilingual detector; repeated runs per scenario.
