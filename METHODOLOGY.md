# Methodology

How the pipeline was built and how to check it yourself. About a day of work, roughly $10 of API calls across every iteration; a single pass over 100 applications costs about $2.50.

## Starting point

- 100 synthetic applications in one [Google Sheet](https://docs.google.com/spreadsheets/d/1PFb-clz0Pqht2sYnyAowENPwcxaWjltTVJlOA9KWwO4/edit?gid=410790500#gid=410790500): 15 reviewed by a human against the rubric, 85 not yet reviewed
- The rubric (`data/rubric.txt`) has two gates. Safety motivation: concern about large-scale outcomes of advanced AI, not only present-day harms. Overall impressiveness: owned, impressive work plus either high context or a named strength area
- The 15 labelled rows went to `data/calibration/`, the 85 to `data/holdout/`. The sets never mix and no labelled row is ever shown to the model as an example

## Steps

1. **Read the 15 side by side before writing anything.** Rewarded: a view-shift answer naming a specific loss-of-control mechanism; a hardest-problem story with ownership, numbers and follow-through; a manager, lead or specialist role in a named strength area. Penalised: present-day-harms-only answers, "I follow the field" answers, associate or coordinator roles executing inside a process, stories the candidate calls contained. One row was a prompt-injection attempt; the human failed it.
2. **Pick the simplest design that could work.** One model call per application with the rubric verbatim. Structured output. Decision rule in code. No fitted model.
3. **Guard the input.** Each field is wrapped in a random delimiter and declared as data. Text addressed to the reviewer is flagged, not followed.
4. **Calibrate against the 15 with labels removed.** Run, compare, revise the prompt, repeat. Revisions had to be rubric clarifications that apply to every candidate; no rule may target a row. Each run is logged in `results/CALIBRATION_LOG.md` with its prompt in `prompts/`.
5. **Add a score behind the verdict.** After the first review round the reviewer wanted to see why one Progress ranked above another. Each gate is now rated 0 to 5 on an anchored scale written into the prompt; the code sets Pass at 3 or more and adds the two ratings for a rank. This replaced a binary priority flag that carried no information beyond the safety verdict.
6. **Stop at the agreement target, then test stability.** Target: at least 90% on the overall decision. Final prompt (v5): both gates 15/15; overall decision 15/15 under the rubric's both-gates rule and 14/15 under the tool's impressiveness-only rule, where the one gap is structural (see the log). Two identical runs produced no verdict changes.
7. **Red team.** Thirteen cases in `redteam.py`: tampered copies of a strong and a weak real application, plus invented junior, buzzword-only, strong and injection-only applications. 11 of 11 checks pass.
8. **Run the 85.** 33 progress, 52 do not progress, $2.05. A second full run during the demo moved 7 decisions at the pass bar in both directions; the log records it and the repo holds the second run.
9. **Build the human step.** A one-file browser UI (`app.py`): drop a CSV, watch the progress bar, then work a queue one row at a time with agree or override and a note. Triage in code decides who is in the queue (everyone who passed the gate plus motivated near-misses) and who is filtered out but still listed (manipulation attempts and clearly weak applications). On the 85: 65 in the queue, 20 filtered out.

## What each prompt version changed

| Version | Change | Reason |
|---|---|---|
| v1 | Rubric verbatim, Pass / Do not pass, one-sentence reasons | Baseline |
| v2 | Reason written before verdict; impressiveness guidance restructured to the rubric's two parts; job title demoted | One verdict contradicted its reason; two owned-story candidates failed on title alone |
| v3 | 0 to 5 anchored scale per gate; verdict derived in code | Reviewer asked for a transparent score behind the rank |
| v4 | The 3 anchor became a three-part checklist; employer names declared weightless | One candidate flipped between 2 and 3 across identical runs |
| v5 | Role level sets a ceiling of 2 for associate-level CVs unless the story shows them leading a hard problem in detail | The checklist let generic-but-numbered associate stories through; the human failed every such case |

## Why this design and not a fitted classifier

- The obvious alternative is to have the model extract features and fit a logistic regression on them. It is more auditable, but it needs tens of labelled examples per class before it matches a large model applying a rubric directly ([Buckmann et al., 2024](https://arxiv.org/abs/2408.03414)). We have 6 and 9. A fitted model on that would learn noise, and the prompt-plus-rule design is already fully readable: the scales are in `prompt.txt`, the rule is twelve lines in `screen.py`
- Injection appears in about 1% of real resumes and can lift a weak candidate over a strong one when candidates look alike, which is exactly this situation ([arXiv:2605.28999](https://arxiv.org/abs/2605.28999); [ACL 2026 Findings](https://aclanthology.org/2026.findings-acl.142/)). Delimiting the untrusted text and flagging instructions rather than ignoring them are the standard low-cost defences, and the red team checks they hold

## Reproduce it

    export ANTHROPIC_API_KEY=...
    uv run screen.py data/calibration/reviewed_candidates_15.csv --out results/my_check --rerun
    uv run calibrate.py results/my_check.csv
    uv run redteam.py

The second command prints agreement per gate and every disagreement with the tool's reason. Expect 15/15 on both gates, occasionally 14. To test a prompt change, edit `prompt.txt`, save a copy under `prompts/`, and rerun.

## Limits of the evidence

- 15 labels from one reviewer, and five prompt versions tried against them. Recalibrate on the first 30 real reviews before trusting the numbers
- The synthetic CVs are templated, so the written answers carry most of the signal. Real CVs will shift the balance
- The rubric requires both gates; the tool relaxes safety motivation to a score component at the reviewer's request. `decide()` in `screen.py` is where to change it
