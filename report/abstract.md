# Abstract

Tool-using language-model agents can be hijacked by instructions hidden in the content they read, a risk called
indirect prompt injection. Benchmarks and defenses for it are mostly described and tested in English, and we
found no comparison of the same attack across languages. We introduce BabelInject, a benchmark in a fully mocked
sandbox where attack success is judged deterministically from the sandbox's action log. It crosses three attack
templates with five languages (English, Nepali, romanized Nepali, Hindi and code-mixed Nepali-English) and four
injection channels (email, file, web page and tool output), and compares four lightweight defenses on the
utility they cost. We evaluate two small local models (Qwen 2.5 3B and 7B) and one hosted 27B model, with one
run per scenario. On the 7B model, attacks succeeded in 35 of 120 English runs and 12 of 120 code-mixed runs,
but in 1 of 120 Nepali and 0 of 240 Hindi and romanized Nepali runs. This is not a failure to understand those
languages: the same text given as the user's own request was followed in 14 of 15 runs, and a prompted detector
recognised the injected text in 20 of 20 runs in every language and channel cell. The 3B model was more exposed in Hindi (10 of 120) than
the 7B, so success is not monotone in model size, and the 27B model was never attacked (0 of 200). In English,
a sandwich reminder cut success from 32 of 60 to 6 of 60 with no loss on benign tasks, while the detector
reached 0 only by withholding tool results, which made every attacked task fail. Cells hold 10 to 120 runs of
one model family, so we report effect sizes with intervals, not precise rates, and make no claim about
frontier models.
