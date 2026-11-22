# Reading guide: the papers to skim (about 1 hour each)

**Why read them:** they are the closest existing work. You must cite them, reuse their task and metric
ideas, and be able to say how this project differs. Interviewers are likely to ask.

**How to find them:** search the title on [arxiv.org](https://arxiv.org). Check authors and year against
the paper itself before citing; this list is from memory and has not been verified.

| Paper (check title on arXiv) | Why it matters to us |
|---|---|
| **AgentDojo**: a dynamic environment to evaluate prompt injection attacks and defenses for LLM agents (Debenedetti et al., 2024) | Closest to our design: a sandboxed environment with tools, benign tasks plus injection tasks, and both utility and attack success measured |
| **InjecAgent**: benchmarking indirect prompt injections in tool-integrated LLM agents (Zhan et al., 2024) | Indirect injection in tool outputs; useful for how attack goals and success are defined |
| **BIPIA**: benchmarking and defending against indirect prompt injection attacks on LLMs (Yi et al., 2023) | Includes defenses; useful for spotlighting and detector ideas |

## What to read (skip the long tables)
1. **Abstract and introduction:** the problem and what they claim.
2. **Threat model / benchmark design:** who the attacker is, what they can control, how tasks are built.
3. **Metric definitions:** exactly how they define attack success and utility. Compare with ours.
4. **Defenses they test** (BIPIA, AgentDojo): the same ideas we implement.
5. **Limitations:** English-only, model sizes, task counts. This is where our contribution fits.

## Write down for the report (5 bullet points is enough)
- What they measured, and how it differs from ours (language, channel, small local models).
- One design idea you borrowed.
- One limitation of theirs that ours addresses.

## Questions to answer after reading
- How do they define a successful attack? Is it deterministic like ours?
- Do they test any non-English text?
- What models did they use, and how big?
