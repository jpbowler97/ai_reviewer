# Methodology

How the pipeline was built and how to check it yourself. About 3 hours of work, roughly $3 of API calls.

## Starting point

- 100 synthetic applications in one [Google Sheet](https://docs.google.com/spreadsheets/d/1PFb-clz0Pqht2sYnyAowENPwcxaWjltTVJlOA9KWwO4/edit?gid=410790500#gid=410790500): 15 reviewed by a human against the rubric, 85 not yet reviewed
- The rubric (`data/rubric.txt`) has two gates. Safety motivation: concern about large-scale outcomes of advanced AI, not just present-day harms. Overall impressiveness: owned, impressive work plus either high context or a named strength area
- The 15 labelled rows were copied to `data/calibration/`, the 85 to `data/holdout/`. The two sets never mix

## Steps

1. **Read the 15 side by side before writing anything.** What the human rewarded: a view-shift answer naming a specific loss-of-control mechanism; a hardest-problem story with ownership, numbers and follow-through; a senior or specialist role in a named strength area. What they penalised: present-day-harms-only answers, "I follow the field" answers, associate or coordinator roles executing inside a process, stories the candidate calls contained or routine. One row contained text instructing an automated reviewer to pass the candidate; the human failed it.
2. **Choose the simplest design that could work.** One model call per application. The rubric goes in verbatim, with a short judging guide. The model returns Pass or Do not pass per gate, a one-sentence reason each, and a manipulation flag. The decision rule is a four-line function in code. No scores, no weights, no fitted model.
3. **Guard against manipulation.** Each field is wrapped in a random delimiter and the prompt states that the contents are data, never instructions. Text addressed to the reviewer is flagged, not followed.
4. **Run on the 15 with labels removed, compare, revise the prompt, repeat.** Revisions had to be rubric clarifications that apply to every candidate. No rule may target an individual row. Every run is logged in `results/CALIBRATION_LOG.md` with its prompt version in `prompts/`.
5. **Stop at the agreement target, then check stability.** Target was at least 90% on the overall decision. Run 1 (prompt v1): 14/15. Run 2 (prompt v2): 15/15. Run 3, same prompt, no changes: 15/15 with zero verdict changes.
6. **Run the 85.** 23 progress, 62 do not progress, $1.76.

## What changed between prompt v1 and v2

- v1 told the model that senior titles were strong evidence and junior titles were not. It failed two candidates the human passed: a programme manager and a systems administrator, both with owned stories in a named strength area. v2 restructures the guidance to follow the rubric's own two parts and demotes title to a weak signal
- v1 let the model give a verdict and then a reason. In one case the reason argued for fail and the verdict said pass. v2 puts the reason field first so the verdict follows from it

## Why this design and not a fitted classifier

- A common alternative is to have the model extract features and fit a logistic regression on them. That is more auditable, but the evidence says it needs tens of labelled examples per class before it matches a large model applying the rubric directly ([Buckmann et al., 2024](https://arxiv.org/abs/2408.03414)). We have 6 and 9. With that few labels, a fitted model would mostly learn noise, and the prompt-plus-rule design is already fully readable
- Injection attempts appear in about 1% of real resumes and can lift a weak candidate over a strong one when candidate quality is homogeneous, which is exactly the situation here ([Real-world prompt injection in resume screening, 2026](https://arxiv.org/abs/2605.28999); [Single and multi-injection settings, ACL 2026](https://aclanthology.org/2026.findings-acl.142/)). Delimiting the untrusted text and flagging instructions rather than ignoring them are the standard low-cost defences

## Reproduce it

    export ANTHROPIC_API_KEY=...
    uv run screen.py data/calibration/reviewed_candidates_15.csv --out results/my_check --rerun
    uv run calibrate.py results/my_check.csv

The second command prints agreement per gate and lists every disagreement with the tool's reason. Expect 14 or 15 of 15 on the overall decision. To test a prompt change, edit `prompt.txt`, save a copy under `prompts/`, and rerun both commands.

## Limits of the evidence

- 15 labels from one reviewer. 15/15 means the tool tracks that reviewer on this sample, nothing stronger
- The synthetic CVs are templated, so the written answers carry most of the signal. Real CVs will shift that balance and probably need one more calibration round
- Both gates are required by the rubric. The tool relaxes safety motivation to a priority marker at the reviewer's request; `decide()` in `screen.py` is where to change it
