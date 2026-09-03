# ai_reviewer

AI-assisted first-pass screening for job applications against a fixed two-gate rubric.
The model extracts evidence and proposes a pass/fail per gate plus a ranking score.
A human reviewer sees the evidence, makes the final call, and their decision is recorded.

Status: scaffold. Pipeline, calibration report, review UI and run instructions to follow.

## Layout

    data/rubric.txt                  the screening rubric, verbatim, single source of truth
    data/calibration/                15 applications with human labels (used only to measure agreement)
    data/holdout/                    85 unlabelled applications the tool is run on
    data/synthetic_applications.xlsx original workbook, both tabs
    src/ai_reviewer/                 pipeline code
    tests/robustness/                adversarial inputs (prompt injection, padding, prestige-only CVs)
    results/                         cached model outputs and human decisions

All applications are synthetic. IDs and names are fictional.

## Principles

- The model recommends; the reviewer decides. Every recommendation ships with verbatim quotes so it can be checked in seconds.
- The 15 labelled rows are a held-out test set, not prompt material. Agreement is reported on all 15.
- The API key is read from the `ANTHROPIC_API_KEY` environment variable only. Nothing secret lives in this repo.
