# Calibration log

Each row is one full run of the 15 labelled candidates. Agreement is with the human labels. Prompt versions are in prompts/.

| Run | Prompt | Safety | Impressiveness | Overall decision | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | v1 | 14/15 | 13/15 | 14/15 | $0.29 | Leila Rook: verdict Pass contradicted the reason (reason said fail). Micah Wren, Kian North: tool failed impressiveness on title level despite owned stories in named strength areas. |
| 2 | v2 | 15/15 | 14/15 | 15/15 | $0.30 | Changes: reason written before verdict; impressiveness guidance restructured to follow the rubric (impressive owned work AND (context OR named strength)); title level demoted to a weak signal. Remaining miss: Micah Wren, tool fails impressiveness where human passed it. Under the tool's decision rule this still lands on Do not progress, matching the human, because the human failed him on safety instead. |
| 3 | v2 | 15/15 | 14/15 | 15/15 | $0.30 | Repeat of run 2 with no changes: zero verdict changes across 30 gate calls. |

Holdout run on the 85: 23 progress (10 high priority, 13 standard), 62 do not progress, no manipulation flags. Cost $1.76. Total spend so far about $2.70.
