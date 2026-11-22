from datetime import date

import pytest

from lib.scout.actionability import assess_title
from lib.scout.ranker import rank_opportunity

TODAY = date(2026, 11, 20)


@pytest.mark.parametrize(
    ("title", "flag"),
    [
        ("Top 26 Language Learning Startups to Watch in 2026", "listicle"),
        ("19 Top Startup Incubators for 2025—and How To Apply", "listicle"),
        ("Kaplan EdTech Accelerator Announces 2014 Class", "news"),
        ("2025 Mastercard Foundation EdTech Fellowship Applications", "past cycle"),
    ],
)
def test_flags_non_actionable_titles(title, flag):
    result = assess_title(title, TODAY)
    assert flag in result.flags
    assert result.multiplier < 1.0


@pytest.mark.parametrize(
    "title",
    [
        "Techstars New York City Accelerator",
        "2027 AI for Education Fellowship — applications open",
        "Fall 2026 – Spring 2027 Founder Grant",  # mentions a current year
    ],
)
def test_leaves_real_opportunities_alone(title):
    assert assess_title(title, TODAY).multiplier == 1.0


def test_penalty_is_applied_and_explained(founder_profile):
    kwargs = dict(snippet="AI EdTech accelerator for pre-seed founders", profile=founder_profile, today=TODAY)
    listicle = rank_opportunity(title="Top 10 EdTech Accelerators", **kwargs)
    program = rank_opportunity(title="EdTech Accelerators", **kwargs)
    assert listicle.scores.total < program.scores.total
    assert "discounted: listicle" in listicle.rank_reason
