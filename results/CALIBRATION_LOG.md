# Calibration log

One row per full run of the 15 labelled candidates. Agreement is with the human labels. Prompt versions are in `prompts/`. "Rubric rule" means Progress needs both gates; "tool rule" means impressiveness alone gates and safety motivation only affects the score. Under the tool rule, Micah Wren (OPS-SYN-004) can never agree: the human passed him on impressiveness and failed him on safety, so the tool progresses him and the human did not. 14/15 is therefore the ceiling under the tool rule.

| Run | Prompt | Safety | Impressiveness | Decision, rubric rule | Decision, tool rule | Cost | What changed and what was learned |
|---|---|---|---|---|---|---|---|
| 1 | v1 | 14/15 | 13/15 | 14/15 | 14/15 | $0.29 | First version, Pass / Do not pass only. One verdict contradicted its own reason. Two candidates failed on job title despite owned stories in a named strength area. |
| 2 | v2 | 15/15 | 14/15 | 15/15 | 15/15 | $0.30 | Reason written before verdict. Impressiveness guidance restructured to follow the rubric's two parts; title demoted to a weak signal. Only miss: Micah Wren failed on impressiveness. |
| 3 | v2 | 15/15 | 14/15 | 15/15 | 15/15 | $0.30 | Repeat, no changes. Zero verdict changes. |
| 4 | v3 | 15/15 | 14/15 | 15/15 | 15/15 | $0.34 | Added 0 to 5 scales per gate; verdicts now derived in code at 3 or more. Same miss as run 2. |
| 5 | v3 | 15/15 | 13/15 | 14/15 | 14/15 | $0.34 | Repeat of run 4. Mara Gale moved from 2 to 3 on impressiveness. The 3 anchor was too loose for associate-level CVs with a numbered but generic story. |
| 6 | v4 | 15/15 | 14/15 | 14/15 | 13/15 | $0.35 | 3 anchor became a three-part checklist and employer names were declared weightless. Stable, but Mara Gale now passes consistently and the human did not pass her. Red team also showed a weak associate crossing to 3 when employers were renamed; the reasons showed it was the same boundary noise, not the employer names. |
| 7 | v4 | 15/15 | 14/15 | 14/15 | 13/15 | $0.35 | Repeat of run 6. Zero changes. |
| 8 | v5 | 15/15 | 15/15 | 15/15 | 14/15 | $0.35 | Role level now sets a ceiling: associate, assistant and coordinator roles score at most 2 unless the story shows them personally leading a hard problem in specific detail. Matches how the human treated every such case. |
| 9 | v5 | 15/15 | 15/15 | 15/15 | 14/15 | $0.35 | Repeat of run 8. Zero verdict changes; two scores moved by one point (Rowan Hart 7 to 8, Nia Jory 1 to 2), neither near a bar. |

Holdout run on the 85 with v5: 33 progress, 52 do not progress, no manipulation flags. $2.05, about 70 seconds. A second full run during the demo recording: 34 progress, 51 not (see the stability note below).

Red team with v5 (`results/REDTEAM.md`): 11 of 11 checks passed.

Total API spend across every run in this log, the red team and the holdout: about $10.

Stability note from use: the 85 were re-screened in full during the demo recording, with the same prompt and model. Compared with the first run, 15 of 85 candidates changed a score by one point and 7 changed decision, all of them moving between impressiveness 2 and 3. The recording showed 33 progress and 52 not; the table in this repo shows 34 and 51, because an interrupted earlier run had left two answers for one candidate at the bar and the repo keeps the later one. The 15 labelled candidates showed no such movement across two runs, but on unlabelled data expect roughly 5 to 10 percent of decisions to sit close enough to the bar to move between runs. The review queue exists for exactly those candidates, and the human sees every one of them.
