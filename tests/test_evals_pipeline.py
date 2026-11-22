from datetime import date
from pathlib import Path

from evals.dataset import FIXTURE_PATH, load_jsonl
from evals.label import stratified_sample
from evals.run import evaluate, main
from lib.scout.profile import load_founder_profile


def test_fixture_eval_runs_and_production_beats_random():
    candidates = load_jsonl(FIXTURE_PATH)
    profile = load_founder_profile(Path("config/founder_profile.example.yaml"))
    rows, _, _ = evaluate(candidates, profile, date(2026, 11, 20), with_ci=False)
    by_name = {row["system"]: row for row in rows}
    assert by_name["keyword_v3 (production)"]["MAP"] > by_name["random"]["MAP"]
    # v2's whole point: the substring traps in the fixture shouldn't fool it.
    assert by_name["keyword_v2 (word match)"]["MAP"] >= by_name["keyword_v1 (substring)"]["MAP"]


def test_cli_writes_report(tmp_path):
    out = tmp_path / "report.md"
    assert main(["--fixture", "--today", "2026-11-20", "--no-ci", "--out", str(out)]) == 0
    assert "| keyword_v3 (production) |" in out.read_text()


def test_stratified_sample_covers_whole_score_range():
    pool = [(c, float(i)) for i, c in enumerate(load_jsonl(FIXTURE_PATH))]  # 30 items, scores 0..29
    picks = stratified_sample(pool, 9)
    scores = {c.id: s for c, s in pool}
    picked = sorted(scores[c.id] for c in picks)
    assert len(picks) == 9
    assert picked[0] < 10 and picked[-1] >= 20  # draws from bottom and top thirds
