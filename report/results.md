# 4. Results (first draft, about 1.3 pages)

Status: draft. Every number is copied from `results/summary/` (tables named in brackets) or
`results/summary_quiet/`; the final numbers check on Nov 26 must re-compare each one. Figures are in
`docs/figures/`. Rates are k/n with 95% Wilson intervals where quoted. One run per scenario, so these
are rates over 10 to 120 runs, not repeated-measure estimates. Section 4.5 and the 27B part of 4.6 wait on
`make run-hosted-quiet`.

**4.1 Language and channel (7B, no defense).** Across the 630-run grid, an attack succeeded in 35 of
120 English runs (29%), 12 of 120 code-mixed (10%), 1 of 120 Nepali, and 0 of 120 each for Hindi and
romanized Nepali [table1]. English success depends on the channel: file 15/30, tool output 11/30, web page
6/30, email 3/30 [table2b]. The model opened the injected item in 90 to 100% of runs in every cell
[table4], so the near-zero non-English rates are not explained by the model skipping the content.
(Fig. 1, 7B heatmap.)

**4.2 Capability control.** When the same text was given as the user's own request, the 7B followed it in
14 of 15 runs, in every language (English 2/3, the other four 3/3; n = 3 per language), so the 7B can act
on Nepali, Hindi and code-mixed instructions and the low injected rates are not a comprehension failure.
The hosted 27B followed direct requests in 1 of 15 runs (only romanized Nepali, 1/3): it refused while
replying in the user's language. (Table A.)

**4.3 Model size.** The 3B model was successfully attacked in 25 of 120 English runs, 10 of 120 Hindi,
6 of 120 code-mixed, 2 of 120 Nepali and 1 of 120 romanized Nepali [table1]. Hindi is the notable
difference: 10/120 on the 3B against 0/120 on the 7B (Wilson intervals about 4.6% to 14.6% against 0% to
3.1%, not overlapping). The 3B also finishes fewer benign tasks (20/30 against 29/30) and opens the
injected item less often (for example file 15/30), so attack success is not monotone in model size and we
do not know why the 3B is vulnerable in Hindi. (Fig. 1, both heatmaps; Table B.)

**4.4 Defenses (7B, English and code-mixed, file, web page and tool output; 60 attacked runs per cell).**

| Defense | English ASR | Code-mixed ASR | Benign utility (n = 30) | Utility on attacked runs |
|---|---|---|---|---|
| none | 32/60 | 12/60 | 29 | 561/600 (full grid) |
| spotlight | 16/60 | 7/60 | 29 | 112/120 |
| sandwich | 6/60 | 0/60 | 30 | 120/120 |
| tool policy | 0/60 | 0/60 | 29 | 105/120 |
| detector | 0/60 | 0/60 | 25 | 0/120 |

[table2, table2b, table3.] The no-defense row here uses the two attacks of the defense grid; it is not the
full-grid English rate of 35/120. Reductions against no defense (percentage points, Newcombe 95%
interval) in English: spotlight 26.7 (9.1 to 42.0), sandwich 43.3 (27.3 to 56.5) [table2]. Tool policy reaches 0% by construction, since no benign task needs `send_email`, so it is a ceiling
rather than a measured robustness. The detector also reaches 0% but flagged all 120 attacked runs and 4 of
30 benign ones, and withholds the tool result, so every attacked task fails (0/120 utility). Sandwich is
the best defense that keeps the task working here. (Fig. 2, Fig. 3.) We did not run defenses on Nepali,
Hindi or romanized Nepali, where the baseline is already about 0%.

**4.5 Address-only follow-up (7B done; 27B pending).** With the attacker address changed to a plausible
partner address and the text otherwise identical, the 7B was still attacked in 10 of 10 English
tool-output runs, and in 6 of 10 English file runs (9 of 10 with the original address; the intervals
overlap), and in 0 of 10 in each of the eight non-English cells [summary_quiet]. So on the 7B the address
is not what limits attack success. Whether it explains the 27B's refusals is **PENDING**.

**4.6 Hosted pilot.** On the first 11 tasks of the hosted grid (76 attacked runs, not a random slice; the
free-tier token quota stopped the run), the 27B was never successfully attacked (0/76, 95% upper bound
4.8%), and finished 11 of 11 benign tasks. Given its refusal of direct requests (4.2), this shows
resistance in these conditions but not which cause explains it.

**4.4b Detector on all five languages (7B).** To separate "cannot recognise" from "recognises but does not
act", we ran the prompted detector on all five languages (file and tool output, 20 runs per cell). It
flagged the injected text in 20 of 20 runs in every cell, and no attacked run sent the attacker email
(0/200) [table6, `results/summary_detector_langs/`]. We expected lower recognition in Nepali and Hindi; we
found none. One caveat: a YES/NO classification is easier than acting on the text.

The benign control addresses the first caveat: on 6 harmless sentences per language, the detector said YES in
1 of 6 English, 0 of 6 Nepali, 0 of 6 romanized Nepali, 0 of 6 Hindi and 1 of 6 code-mixed runs
[table7], so the 20/20 flags are not a general bias against non-English text. With 6 runs per language, a
rate up to about 39% cannot be excluded.
