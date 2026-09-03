"""Tests that run without an API key. Run with: uv run --with pytest pytest -q"""
import csv, importlib.util, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("screen", ROOT / "screen.py")
screen = importlib.util.module_from_spec(spec); spec.loader.exec_module(screen)


def test_decision_rule():
    d = screen.decide(4, 4)
    assert (d["Overall decision"], d["Score /10"], d["Why"]) == ("Progress", 8, "Both gates met")
    d = screen.decide(1, 3)
    assert d["Overall decision"] == "Progress" and d["Safety motivation"] == "Do not pass" and d["Score /10"] == 4
    d = screen.decide(5, 2)
    assert d["Overall decision"] == "Do not progress" and d["Why"].startswith("Impressiveness 2/5")
    assert screen.decide(0, 0)["Score /10"] == 0


def test_triage():
    assert screen.triage(4, 4, False) == "Review"
    assert screen.triage(4, 2, False) == "Review"          # borderline miss, motivated
    assert screen.triage(2, 2, False) == "Filtered out"    # missed the gate, unmotivated
    assert screen.triage(5, 1, False) == "Filtered out"
    assert screen.triage(5, 5, True) == "Filtered out"     # manipulation always filtered


def test_prompt_contains_rubric_verbatim():
    rubric = (ROOT / "data/rubric.txt").read_text(encoding="utf-8-sig").strip()
    assert rubric in screen.PROMPT
    assert "{rubric}" not in screen.PROMPT


def test_message_wraps_every_field_with_one_random_tag():
    row = {"Synthetic ID": "X-1", "Synthetic name": "n", "CV text": "cv", "AI-risk view shift": "vs", "Hardest problem": "hp"}
    m1, m2 = screen.build_message(row), screen.build_message(row)
    assert m1 != m2                      # delimiter changes per call
    for f in screen.FIELDS:
        assert f'name="{f}"' in m1
    assert m1.count("_FIELD name=") == 3 and m1.count("</") == 3   # 3 opening + 3 closing tags


def test_input_files_have_expected_columns_and_are_disjoint():
    cal = list(csv.DictReader(open(ROOT / "data/calibration/reviewed_candidates_15.csv", encoding="utf-8-sig")))
    hold = list(csv.DictReader(open(ROOT / "data/holdout/candidates_to_process_85.csv", encoding="utf-8-sig")))
    assert len(cal) == 15 and len(hold) == 85
    for col in [screen.ID, screen.NAME, *screen.FIELDS]:
        assert col in cal[0] and col in hold[0]
    assert not {r[screen.ID] for r in cal} & {r[screen.ID] for r in hold}


def test_write_outputs_orders_progress_then_score(tmp_path):
    rows = [{"Synthetic ID": f"X-{i}", "Synthetic name": "n", "CV text": "c", "AI-risk view shift": "v", "Hardest problem": "h"} for i in range(3)]
    base = {"safety_reason": "a", "impressiveness_reason": "b", "manipulation_attempt": False}
    results = [
        {**base, "safety_score": 5, "impressiveness_score": 2, "manipulation_attempt": True},  # 7 but fails the gate
        {**base, "safety_score": 0, "impressiveness_score": 3},                                 # 3, progress
        {**base, "safety_score": 3, "impressiveness_score": 4},                                 # 7, progress
    ]
    out = tmp_path / "t"
    screen.write_outputs(rows, results, out)
    got = list(csv.DictReader(open(out.with_suffix(".csv"))))
    assert [g["Synthetic ID"] for g in got] == ["X-2", "X-1", "X-0"]
    assert got[2]["Queue"] == "Filtered out" and got[0]["Queue"] == "Review"
    assert got[2]["Flags"] == "Manipulation attempt" and got[2]["Why"].startswith("Impressiveness 2/5")
    assert "Reviewer decision" in got[0] and out.with_suffix(".xlsx").exists()
