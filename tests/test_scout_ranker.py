from datetime import date, timedelta

from lib.scout.ranker import _deadline_score, rank_opportunity
from lib.text import substring_hits
from tests.conftest import TODAY


def _rank(profile, title, snippet="", **kw):
    return rank_opportunity(title=title, snippet=snippet, profile=profile, today=TODAY, **kw)


def test_relevant_opportunity_outscores_irrelevant_one(founder_profile):
    relevant = _rank(
        founder_profile,
        "Pre-seed grant for AI EdTech startups",
        "Funding for machine learning tools that support language learning in "
        "underresourced and indigenous languages. BIPOC founders encouraged.",
        category="grants",
    )
    irrelevant = _rank(
        founder_profile,
        "Restaurant franchise expo",
        "Email us to maintain your booth. Said to be the largest food fair.",
        category="other",
    )
    assert relevant.scores.total > irrelevant.scores.total + 30
    assert relevant.rank_reason.startswith("Strong")
    assert irrelevant.rank_reason.startswith("Moderate")


def test_word_boundary_matching_removes_false_ai_signal(founder_profile):
    text = "Email the team; they said maintenance grants are available"
    word = _rank(founder_profile, text)
    legacy = _rank(founder_profile, text, matcher=substring_hits)
    assert word.scores.ai_focus == 0.0
    assert legacy.scores.ai_focus > 0.0  # the bug the matcher change fixed


def test_total_is_weighted_sum_of_components(founder_profile):
    ranked = _rank(founder_profile, "AI education grant", "pre-seed founders")
    s, w = ranked.scores, founder_profile.priorities
    expected = (
        s.stage_fit * w.stage_fit
        + s.ai_focus * w.ai_focus
        + s.education_focus * w.education_focus
        + s.language_preservation * w.language_preservation
        + s.minority_founder * w.minority_founder
        + s.deadline * w.deadlines
    )
    assert abs(s.total - round(expected, 1)) < 1e-9


def test_scores_are_bounded(founder_profile):
    kitchen_sink = " ".join(
        founder_profile.signals.ai_keywords
        + founder_profile.signals.education_keywords
        + founder_profile.signals.language_preservation_keywords
        + founder_profile.signals.minority_founder_keywords
    )
    ranked = _rank(founder_profile, kitchen_sink, deadline_at=TODAY + timedelta(days=3))
    for value in ranked.scores.model_dump().values():
        assert 0.0 <= value <= 100.0


def test_deadline_score_buckets():
    assert _deadline_score(None, TODAY) == 10.0
    assert _deadline_score(TODAY - timedelta(days=1), TODAY) == 0.0
    assert _deadline_score(TODAY + timedelta(days=7), TODAY) == 100.0
    assert _deadline_score(TODAY + timedelta(days=30), TODAY) == 70.0
    assert _deadline_score(TODAY + timedelta(days=90), TODAY) == 40.0
    assert _deadline_score(date(2030, 1, 1), TODAY) == 20.0
