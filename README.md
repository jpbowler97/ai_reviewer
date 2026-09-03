# ai_reviewer

First-pass screen of job applications against a two-gate rubric. The model reads each application once, records Pass or Do not pass on each gate with a one-sentence reason, and the reviewer gets a ranked spreadsheet. The reviewer makes the final call.

## What it does

- One model call per application, sending the rubric verbatim plus the CV and two written answers
- Returns four things per candidate: safety motivation verdict and reason, impressiveness verdict and reason, plus a manipulation flag
- Decision rule (in code, one function): impressiveness is the hard gate; safety motivation sets priority among those who progress
- Output is the input table plus five columns: the two gate verdicts, decision, priority, reasons and flags. Sorted High priority, Standard, then Do not progress
- Anything inside the application addressed to the reviewer or the system is treated as data and flagged, not followed

## Run it

1. Install uv (one line, https://docs.astral.sh/uv/). Nothing else to install.
2. Put your key in the shell: `export ANTHROPIC_API_KEY=...`
3. Export applications from the applicant system as a CSV with these columns: `Synthetic ID, Synthetic name, CV text, AI-risk view shift, Hardest problem`
4. Run:

        uv run screen.py path/to/applications.csv

5. Open `results/<file name>.xlsx`

Reruns skip candidates already screened, so adding new rows to the CSV and running again only costs the new rows. `--rerun` forces a fresh pass. To screen one new application, put it in a one-row CSV and run the same command.

## Cost and speed

- About 3,300 tokens in and 160 out per application on claude-opus-5 at low effort
- 85 applications: $1.76, 62 seconds
- 1,000 applications: roughly $20 and 12 minutes

## Calibration

15 human-labelled applications, held out from prompt design and never used as examples. Log with every run in `results/CALIBRATION_LOG.md`; side-by-side sheet in `results/calibration_comparison.xlsx`.

- Safety motivation: 15/15
- Overall impressiveness: 14/15
- Overall decision: 15/15, identical on a repeat run
- Two prompt versions were needed (`prompts/`). The one change of substance: the first version over-weighted job title; the rubric asks for owned work with results in a named strength area

## Files

    screen.py          the pipeline (about 150 lines)
    prompt.txt         the instructions the model gets; read this to understand every judgement
    calibrate.py       compares a results file with the human labels
    data/rubric.txt    rubric, verbatim
    data/calibration/  15 labelled applications
    data/holdout/      85 to process
    results/           outputs, cache of raw model answers, calibration log
    tests/             offline tests: uv run --with pytest --with anthropic --with pydantic --with openpyxl pytest -q tests

## Limits

- 15 labels is a small set. Agreement of 15/15 says the tool is close to one reviewer on this sample, not that it is right in general
- The CVs are synthetic and templated, so most signal is in the two written answers. Real CVs will carry more of the load and the prompt may need one more calibration pass
- The rubric's own rule is that both gates are needed to progress. This tool relaxes that: safety motivation sets priority rather than blocking. Change one line in `decide()` to restore the strict rule
- Every judgement is one model call with no second opinion. Reviewer disagreements should be logged to improve the prompt
