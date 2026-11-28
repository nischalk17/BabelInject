# 5. Discussion and limitations

**What the results support.** For these models and settings, indirect injection against a tool-using agent works
in English and code-mixed text, depends strongly on where the text appears, and barely works in Nepali, romanized
Nepali or Hindi on the 7B model. The capability control shows this is not because the 7B cannot follow those
languages: it followed direct requests in 14 of 15 runs, and the detector recognised the injected text in every
language. The pattern is consistent with a model that understands the text but does not act on it, but we did not
test that explanation directly. Defenses differ sharply in cost: sandwich cut English attack success from 32/60 to
6/60 with no benign utility loss (30/30), while the detector reached 0% only by withholding tool results, so every
attacked task failed, and in a sixth of its runs the agent looped until the step limit. Attack success is not
monotone in model size: the 3B was more exposed in Hindi (10/120) than the 7B (0/120).

**Relation to prior work.** Three of our observations line up with published findings, though models, tasks and
attacks differ, so we call them consistent, not confirming. Delimiting roughly halved attack success on the 7B
(English 32/60 to 16/60), the size of effect the spotlighting authors report for delimiting alone, and they too do
not recommend it by itself [5]. The detector's utility cost matches AgentDojo's report that a detector's false
positives significantly degrade utility [4], although our detector is a prompted LLM and theirs is a classifier. And
capability and attack success moved together in English (7B 35/120, 3B 25/120), as BIPIA and AgentDojo report for
more capable models [2, 4], but not in Hindi (3B 10/120, 7B 0/120). Our
language result runs the other way from the jailbreak studies, in which low-resource languages elicit more unsafe
output [6, 7]; those studies use direct requests and much larger models, so the two are not comparable.

**What they do not support.** We cannot say Nepali or Hindi are "safer": zero success on one small model, for three
author-reviewed attack texts, is a floor result. It leaves no room to measure a defense, and the capability control
rules out only an inability to follow the language, not other explanations. We cannot say anything about large
frontier models. The only larger model is a hosted 27B run with one pass per scenario; it was never attacked
(0/200), including in English, where the 7B was attacked in 26 of 40 matched runs, so its result is not specific to
non-English text, and we do not know why it refuses direct requests (a plainer attacker address did not change this:
1/100 injected runs). We saw one defense language gap, on the 3B (the detector flags Hindi attacks about half as
often as English ones; n = 40 per cell), and none on the 7B. We cannot say defenses in general work in Nepali, Hindi or
romanized Nepali: only the detector was run there (it flagged all 20 of 20 runs per cell, and flagged 0 of 6 harmless
Nepali, romanized Nepali and Hindi sentences); spotlighting, sandwich and tool policy were not. We do not know why the
3B is vulnerable in Hindi.

**Limitations.**

- One model family (Qwen 2.5, plus one hosted Qwen); one run per scenario at temperature 0; cells hold 10 to 120
  runs, so intervals are wide, and runs share task facts, so they are somewhat optimistic.
- Three attack templates, written for this study; non-English texts were AI-drafted and author-reviewed. A different
  wording could change the rates, and we did not test wording.
- The attacker's goal is one action (sending an email) to one address. The address is conspicuous; the follow-up
  with a plain address changed the 7B's English file rate from 9/10 to 6/10, within the intervals.
- Tool policy reaches 0% by construction (no benign task needs `send_email`), so it is a ceiling, not a measured
  defense. The detector and sandwich prompts are in English. Spotlighting is the delimiting form only.
- The capability control has only 3 runs per language, and the 3B often never reads the injected item, which limits
  what its rates mean.
- The hosted grid is a subset (two attacks, two channels) and, like the hosted address-only run, was spread over
  several days by the free-tier quota. The provider's system fingerprint changed six times during the grid, so these
  runs are not one fixed deployment.
- The "answer mentions the injection" measure is a keyword rule validated only on the 27B; it is descriptive and is
  not used for any attack-success number.
- The sandbox is mocked and the goal is one action; real deployments differ.

**Future work.** Less conspicuous attacks and varied wording in Nepali and Hindi; larger and non-Qwen models;
defenses tested in non-English languages; a multilingual detector prompt; repeated runs per scenario to measure
run-to-run spread; and an investigation of why romanized Nepali is the one language where the 27B less often
mentions the injection (34 of 40 against 39 or 40 of 40 elsewhere).
