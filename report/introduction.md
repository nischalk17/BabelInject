# 1. Introduction

A language-model *agent* does more than chat. It reads email, opens files and web pages, and calls tools such as
`send_email` on the user's behalf. That is useful, and it creates an attack surface: any text the agent reads can
contain instructions, and a model that cannot tell the user's instructions from the data it is processing may
follow them. This is *indirect prompt injection* [1]. An attacker who can put a sentence into an email, a shared
document, a web page or a tool's output can try to make the agent do something the user never asked for, such as
sending private information to an address the attacker controls.

Three benchmarks measure this risk and several defenses have been proposed [2, 3, 4, 5]. Two gaps motivate this
work. First, language. Many people who use assistants do not write only in English, and in South Asia
everyday messages often mix scripts and languages: Nepali in Devanagari, Nepali typed in Latin letters ("romanized"),
Hindi, and sentences that switch between Nepali and English. Studies of direct jailbreaks show that the language
of a request changes how models respond [6, 7], but in the injection benchmarks we read we found no comparison of
the same attack written in different languages. A defense built and tested on English text may not carry over, and
a detector that never saw Nepali may miss a Nepali attack. Second, model size. Benchmarks mostly evaluate large
hosted models, but many people and organisations run small open models locally because of cost and privacy, and it
is unclear how those behave.

We therefore ask three questions.

- **RQ1.** How does the attack success rate vary with language and with the channel through which the attack
  arrives, for small open models?
- **RQ2.** Do lightweight defenses (delimiting, a task-reminder "sandwich", a tool-permission policy and a prompted
  injection detector) work as well on non-English attacks as on English ones?
- **RQ3.** What does each defense cost in benign task success?

A zero attack rate in a language can mean two different things: the model resists the attack, or the model cannot
read the language and never understood it. Reporting either as "this language is safe" would be a mistake, so
the study adds a *capability control*. The same attack text is given to the model as the user's own request, so
that a model which follows it there but not when it is injected is shown to understand the language.

**Contributions.**

1. *BabelInject*, an open benchmark in a fully mocked sandbox (no real email, web or file system is touched). It
   has 30 benign tasks (10 facts, each stored as an email, a file and a web page), three attack templates in five
   languages, four channels, four defenses and a deterministic judge that decides success from the sandbox's
   action log. Every experiment is a configuration file, every model call is cached and every result row records
   the model tag.
2. Measurements of attack success by language and channel on three models (Qwen 2.5 3B and 7B run locally, and a
   hosted 27B model), with the capability control, a detector probe on all five languages with a benign control,
   and a follow-up that separates the effect of the attacker's address from the effect of language.
3. A comparison of the four defenses on the same grid, with their cost in benign and attacked task success, and a
   small pilot of the defenses on Hindi against English on the 3B model.

We state the limits plainly. The study uses one model family, one run per scenario, cells of 10 to 120 runs and three
author-written attack templates. We therefore report effect sizes with intervals, make no claim about frontier
models, and do not claim that any language is safer.

**Roadmap.** Section 2 reviews related work, Section 3 describes the method, Section 4 reports the results,
Section 5 discusses what they do and do not support, and Section 6 concludes. Section 7 covers reproducibility and
ethics.
