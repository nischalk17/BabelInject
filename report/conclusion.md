# 6. Conclusion

We built BabelInject, a mocked-sandbox benchmark with a deterministic judge, and used it to ask whether
lightweight defenses against indirect prompt injection hold up across languages and channels for small open
models. Four findings stand on the data. First, attack success depends strongly on both language and channel:
on the 7B model it was 29% for English and 10% for code-mixed text, but near zero in Nepali, romanized Nepali and
Hindi, and in English it ranged from 10% in email to 50% in files. Second, the near-zero non-English rates are not
a comprehension failure. The 7B followed the same text as a direct request in 14 of 15 runs, and the detector
recognised the injected text in all 20 runs of every language and channel cell, so the model understands the text
and, in these conditions, does not act on it. We have not tested why. Third, success is not monotone in model size:
the 3B model, which is less capable, was attacked in Hindi (10 of 120) where the 7B never was, and the 3B detector
flagged Hindi attacks about half as often as English ones, the only defense language gap we measured. The hosted 27B
model was never attacked (0 of 200). Fourth, defenses differ sharply in cost. A sandwich reminder cut English
success from 32 of 60 to 6 of 60 at no cost on benign tasks, delimiting halved it, the tool policy reached zero by
construction, and the prompted detector reached zero only by withholding tool results, so every attacked task
failed.

For practice, the results suggest three things. A defense tested in English should not be assumed to work in the
language of the deployment; the one defense we measured in Hindi and English behaved differently on the smaller
model. A zero success rate in a language needs a capability control before it is read as safety. And controls
that act on the agent's actions rather than its text, such as a tool-permission policy, do not depend on language
at all, but they work only when the policy fits the tasks.

The evidence is small by design: one model family, one run per scenario, three attack templates, and defenses
other than the detector tested only in English and code-mixed text. The claims above hold for these models and
settings. The natural next steps are subtler attacks and varied wording in Nepali and Hindi, repeated runs
per scenario, a non-Qwen model family and larger models, the other defenses in non-English languages, and a
multilingual detector prompt.
