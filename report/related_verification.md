# Verification of the related-work claims (2026-11-28)

**Purpose.** `report/related.md` makes claims about seven papers. This file records, claim by claim, what was
checked, against which text, and what could not be checked, so that the author can confirm the remaining
points in minutes. It replaces the earlier abstract-level check of 2026-11-23.

**Method.** For each paper a reader fetched the arXiv abstract page and the arXiv HTML version of the full
text (the PDF links returned unreadable binary). Venues and pages were then checked on the publisher pages
(ACM Digital Library, ACL Anthology, NeurIPS). Status words: **VERIFIED** (read in the text), **CORRECTED**
(the earlier draft was wrong or imprecise and is fixed), **NOT CHECKED** (not read in verbatim text).
Figures that came only from an automatic summary of a page, not from verbatim text, are marked
*summary-derived* and are **not** used in the report.

## Corrections made to the earlier draft

| Earlier claim | Finding | Action |
|---|---|---|
| AgentDojo "reports attacks succeeding in under 25% of cases against the best agents" | The introduction says so, but the paper's own later tables (summary-derived) appear to give higher rates for some models (for example about 48% for one model). We could not reconcile the two. | **Removed.** The figure is not used. |
| AgentDojo "a secondary detector lowering this to 8%" | The paper says that deploying existing defenses "such as a secondary attack detector" makes attack success "drop to 8%", and that the detector "has too many false positives" and "significantly degrades utility". The 8% is not a drop from "under 25%". | **Rewritten** with the utility cost stated. |
| "AgentDojo ... NeurIPS 2024 Datasets and Benchmarks" | The arXiv page has no venue field. | **VERIFIED** on the NeurIPS 2024 poster page (neurips.cc/virtual/2024/poster/97522). |
| "InjecAgent ... 62 attacker tools" | The abstract says "62 different attacker tools", the body says 62 attacker cases (instructions): 30 direct-harm and 32 data-stealing. | **Reworded** to "62 attacker cases". |
| BIPIA "proposes boundary-awareness and explicit-reminder defenses" | Confirmed by the ACM abstract, but the body's black-box methods are an explicit reminder, a multi-turn dialogue format and in-context learning; the white-box method fine-tunes with data tokens and adversarial training. | **Reworded** to the body's description. |
| "these works, as far as their abstracts state, evaluate English" | None of the three texts states a language scope either way. | **Reworded** to "we found no comparison of the same attack across languages". |
| "Third, judging: success is decided deterministically ... never by an LLM" listed as a difference | AgentDojo (state checks) and InjecAgent (rule on the parsed tool call) are also deterministic; only BIPIA uses an LLM judge in part. | **Removed as a difference**; the text now says it is not new. |
| "reports lowering attack success from over 50% to under 2%" (spotlighting) | Abstract wording is "greater than 50% to below 2%"; the largest reductions are for datamarking and encoding; delimiting only "can reduce the ASR by half"; the authors "do not recommend using delimiting in practice". | **Reworded**; this matters because our spotlighting is delimiting only. |

## BIPIA (Yi et al., KDD 2025; arXiv:2312.14197)

| Claim in the report | Status | Evidence |
|---|---|---|
| Authors Yi, Xie, Zhu, Kiciman, Sun, Xie, Wu; KDD 2025, pp. 1809-1820, doi:10.1145/3690624.3709179 | VERIFIED | arXiv metadata ("Accepted by KDD 2025"); ACM DL page (published 20 July 2025; KDD '25, Toronto, 3-7 Aug 2025) |
| Five scenarios: email QA, web QA, table QA, summarization, code QA | VERIFIED | Table 1 and Section 4 |
| 250 attacker goals = 30 text + 20 code attack types x 5 instructions | VERIFIED | Section 4 ("30 types of text attacks and 20 types of code attacks, each containing five specific malicious instructions") |
| 25 LLMs evaluated | VERIFIED | Introduction; Table 2 has 25 rows |
| Positive association between capability and attack success on text attacks, none on code attacks | VERIFIED | Contributions; Section 5, "Impact of LLM's capability"; Fig. 2 caption (Pearson 0.64 text, -0.03 code). The authors call the explanation speculative |
| Prompt-level tasks, not tool-calling agents | VERIFIED | Sections 4 and 5; tools appear only as motivation |
| Success computed with rules, an LLM judge and language detection | VERIFIED (Section 5) | Which attack type uses which judge: **NOT CHECKED** |
| Black-box defenses (explicit reminder, multi-turn dialogue, in-context learning); white-box (data tokens + adversarial fine-tuning) | VERIFIED | Sections 6.1 and 6.2; abstract says the white-box method reaches near-zero attack success |
| Defense numbers (for example Vicuna ASR before and after) | NOT CHECKED | Only in a summary whose baselines disagree with the verbatim Table 2; **not used** |
| Limitations section and any statement on languages | NOT CHECKED | Section 8 and the appendices were not read verbatim |

## InjecAgent (Zhan et al., Findings of ACL 2024; arXiv:2403.02691)

| Claim in the report | Status | Evidence |
|---|---|---|
| Authors Zhan, Liang, Ying, Kang; Findings of ACL 2024, pp. 10471-10506, doi:10.18653/v1/2024.findings-acl.624 | VERIFIED | ACL Anthology entry; arXiv comment "ACL 2024 Findings" |
| 1,054 test cases = 17 user cases x 62 attacker cases | VERIFIED | Abstract; Section 2.2; Table 2 (17 x 62 = 1,054) |
| 30 direct-harm and 32 data-stealing attacker cases | VERIFIED | Section 2.2 and Table 1 |
| 30 agents evaluated (two fine-tuned: GPT-3.5 and GPT-4) | VERIFIED | Abstract; Sections 3.1 and 8 |
| ReAct-prompted GPT-4: 24% attack success, 47% with the hacking prompt | VERIFIED | Section 1 and Section 3.2 text; Table 3 is captioned ASR-valid and its GPT-4 totals round to 24 and 47 (our reading of a flattened table) |
| Static, simulated tool responses with an attacker-instruction placeholder | VERIFIED | Sections 2.2, 2.3 and B.2; the user's tool call is assumed already made |
| Success judged by rule on the parsed tool call (data stealing: extraction, then sending) | VERIFIED | Sections 2.3 and 3.1; invalid outputs are excluded in ASR-valid |
| No defense is evaluated | VERIFIED | Section 5 only describes prior defenses |
| Languages | NOT CHECKED | No statement either way was found |
| Note | Internal inconsistency in the paper | Section 3.2 gives the fine-tuned GPT-4 base ASR as 3.8%, Table 3 gives 6.6% (3.8% is GPT-3.5). Not used in the report |

## AgentDojo (Debenedetti et al., NeurIPS 2024 D&B; arXiv:2406.13352)

| Claim in the report | Status | Evidence |
|---|---|---|
| Authors Debenedetti, Zhang, Balunovic, Beurer-Kellner, Fischer, Tramer; NeurIPS 2024 Datasets and Benchmarks, vol. 37, pp. 82895-82920 | VERIFIED | NeurIPS poster page; pages from the proceedings listing as cited by other papers (**check the page range on proceedings.neurips.cc before citing**) |
| Stateful, extensible environment; dummy data; four suites (workspace, Slack, travel, banking) | VERIFIED | Abstract; Section 3.1; checklist ("only dummy data") |
| 97 user tasks and 629 security test cases | VERIFIED | Abstract; Section 4 |
| Utility and security are deterministic functions of outputs and state, not an LLM judge | VERIFIED | Section 3.1 ("a deterministic binary function"); Section 2 contrasts this with LLM evaluators |
| Metrics: benign utility, utility under attack, targeted attack success | VERIFIED | Section 3.4 |
| More capable models tend to be easier to attack ("a form of inverse scaling law") | VERIFIED | Section 4.1 |
| Injections near the end of a tool response are most effective | VERIFIED | Section 4.1 ("up to 70% average success rate against GPT-4o") |
| Four defense families: delimiters (following spotlighting), detector, repeating the user prompt, tool filter | VERIFIED | Section 4.3 |
| Detector: attack success "drops to 8%" but "significantly degrades utility" | VERIFIED | Introduction and Section 4.3 (the 8% is the paper's own wording) |
| Tool filter fails when needed tools are also sufficient for the attack | VERIFIED | Section 4.3 (17% of test cases) |
| Per-model and per-defense table values (Tables 3-5) | NOT CHECKED | Summary-derived only; **not used**. The paper also seems internally inconsistent in places (tool count 70 vs 74; tool-filter 7.5% vs 6.84%; whether the adaptive "Max" attack beats "Important message") |
| Languages | NOT CHECKED | No statement either way was found |

## Spotlighting (Hines et al.; arXiv:2403.14720)

| Claim in the report | Status | Evidence |
|---|---|---|
| Authors Hines, Lopez, Hall, Zarfati, Zunger, Kiciman (Microsoft); submitted 20 Mar 2024 | VERIFIED | arXiv abstract page |
| Published venue | NOT FOUND | Cited as an arXiv preprint |
| Three techniques: delimiting, datamarking, encoding | VERIFIED | Sections III-B to III-D |
| "From greater than 50% to below 2%" with GPT-family models | VERIFIED | Abstract, verbatim |
| Datamarking, GPT-3.5-Turbo summarization: about 50% to below 3% (3.10%) | VERIFIED | Section V-A, Fig. 4 |
| Delimiting: baseline about 60% on GPT-3.5-Turbo, "can reduce the ASR by half"; authors "do not recommend using delimiting in practice" | VERIFIED | Fig. 3; Section III-B |
| Encoding works only with the most capable models | VERIFIED | Section V-B |
| Evaluation: 1,000 synthetic documents with a keyword payload; success by keyword output | VERIFIED | Sections IV-A and IV-B |
| The sandwich defense and non-English text | NOT FOUND | Neither appears in the text read; the sandwich is attributed to AgentDojo instead |

## Language and safety papers

| Claim in the report | Status | Evidence |
|---|---|---|
| Deng et al.: ICLR 2024 (arXiv comment); low-resource languages about three times as likely to elicit harmful content (unintentional); 80.92% (ChatGPT) and 40.71% (GPT-4) unsafe in the intentional scenario | VERIFIED | Abstract and Table 1, verbatim. Acceptance at ICLR is from the arXiv comment only (**check the ICLR page**) |
| Deng et al.: no Nepali; Hindi appears at most in the 30-language preliminary study | VERIFIED for the nine-language MultiJail set (Section 3.1); the 30-language list is **NOT CHECKED** (summary only) |
| Yong et al.: 79% of low-resource-translated AdvBench prompts engaged by GPT-4, under 1% in English; Hindi 6.54%, Bengali 13.27%; Zulu, Scots Gaelic, Hmong, Guarani are the low-resource set; no Nepali | VERIFIED | Abstract, Section 4.1, Table 1. The venue (NeurIPS 2023 SoLaR workshop, best paper) is from the arXiv comment only |
| Both studies concern direct harmful requests, not indirect injection or agents | VERIFIED | Not discussed in the text read |
| Judging: Yong et al. human annotation (BYPASS/REJECT/UNCLEAR); Deng et al. human evaluators and GPT-4 (kappa 0.86) | VERIFIED | Sections 3.2 and 2.1-2.2 |

## Foundational citations

| Claim | Status | Evidence |
|---|---|---|
| Greshake et al., "Not what you've signed up for", arXiv:2302.12173 (23 Feb 2023); introduces indirect prompt injection | VERIFIED | arXiv abstract page. Its publication venue was **not checked** (cited as arXiv) |
| Yao et al., ReAct, ICLR 2023, arXiv:2210.03629 | VERIFIED | arXiv and ICLR pages |
| Wilson (1927), Newcombe (1998) | NOT CHECKED here | Standard statistical references, cited from knowledge; the Newcombe method-10 example is reproduced by a unit test (`test_newcombe_matches_the_published_example`) |

## What the author should still confirm (about 20 minutes)

1. AgentDojo page range on proceedings.neurips.cc, and Deng et al. on the ICLR 2024 site.
2. BIPIA Section 5: which judge applies to which attack type (one sentence in the report depends on it).
3. A skim of each paper's limitations section for any statement about languages (none was read for BIPIA, and
   none was found for the others). If any of them states "English only", the sentence in Section 2 can
   become stronger.
4. That the descriptions of the three papers in Table 1 match how you would summarise them.
