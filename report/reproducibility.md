# 7. Reproducibility, ethics and availability

**Code, data and demo.** The benchmark, analysis code, configuration files, summary tables and figures are in the
public repository `https://github.com/nischalk17/BabelInject` (MIT license; the release version is in
`CITATION.cff`). A read-only Results Explorer built from the same summary data is at
`https://nischalk17.github.io/BabelInject/`. It computes no statistics in the browser and calls no model.

**Reproducing the results.** Every experiment is a file in `configs/`; no setting is hard-coded.

```
make setup                 # install dependencies
make run-all               # 3B/7B no-defense grid (630 runs; hours on CPU)
make run-defenses          # five defenses on the 7B (750 runs)
make run-hosted            # hosted 27B grid (needs a Groq key in .env; several days on the free tier)
make check CONFIG=configs/full.yaml    # confirms the rows on disk cover the whole grid
make figures               # tables (results/summary/*.csv) and figures (docs/figures/*.png)
```

Every model call goes through a response cache at temperature 0 and seed 0, and every result row stores the model
tag (for local models the tag includes the first twelve characters of the weights digest), the prompt version, the
defense version and, for hosted runs, the model id and system fingerprint the provider returned. Raw result rows
are not committed; the summary CSVs are, and each figure has a CSV twin. A re-run reproduces the actions of an
earlier run in the checks we made (10 of 10 repeats), but output wording is not bit-for-bit reproducible, and a
hosted model may change between runs (Section 4.8).

**Ethics.** All data is fictional. The sandbox never reaches a real mailbox, web page or file system, and no real
person's data is used. The attacker address uses the reserved `.test` domain. The attack texts ask an agent to
send one email to a fictional address; they contain no exploit code and no new technique, and the study is
defensive in purpose. Findings that a defense fails (for example the 3B detector in Hindi) are reported so that
defenses can be tested in the languages they will serve.

**Provenance of the attack texts.** The non-English attack texts were first drafted by an AI assistant and then
reviewed and corrected line by line by the author, who reads Nepali and Hindi (`docs/TRANSLATIONS.md`).

**Use of AI assistance.** The code, the analysis scripts and the drafts of this report were written with the help
of an AI assistant (Claude, Anthropic) under the author's direction and review. Every number in the report comes
from the repository's result files through its analysis code, and a scripted check compares each fraction in the
text with the tables (Appendix B). The related-work descriptions were checked against the cited papers' full text
(`report/related_verification.md`).
