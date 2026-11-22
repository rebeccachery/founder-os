from datetime import date

import pytest

from lib.scout.ranker import parse_deadline_from_text
from tests.conftest import TODAY


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Application deadline: March 4, 2027", date(2027, 3, 4)),
        ("Apply by Sept. 30, 2026 to be considered", date(2026, 9, 30)),
        ("Applications close 25 June 2026.", date(2026, 6, 25)),
        ("Deadline 2026-07-15 (11:59pm PT)", date(2026, 7, 15)),
        ("Submit by 06/24/2026", date(2026, 6, 24)),
        ("Deadline: 24/06/2026", date(2026, 6, 24)),  # DD/MM fallback when first part > 12
        ("Deadline: December 12, 202*****6**", date(2026, 12, 12)),  # markdown split the year
        ("Apply by Sep 8th", date(2026, 9, 8)),  # year inferred: nearest to today
    ],
)
def test_parses_supported_formats(text, expected):
    assert parse_deadline_from_text(text, today=TODAY) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Posted March 4, 2026 — a new program for founders",  # date, but no deadline language
        "Applications close in 30 days",  # relative: anchored to an unknown publish date
        "No dates here at all",
        "",
    ],
)
def test_returns_none_without_trustworthy_deadline(text):
    assert parse_deadline_from_text(text, today=TODAY) is None


def test_prefers_date_after_keyword_over_date_before_it():
    text = "Applications open: May 1, 2026 / Deadline: June 30, 2026"
    assert parse_deadline_from_text(text, today=TODAY) == date(2026, 6, 30)


def test_stale_article_keeps_its_own_year_and_reads_as_expired():
    # A 2024 article saying "applications close November 1" must not be
    # bumped into the future — the year mentioned in the snippet wins.
    text = "2024 cohort: applications close November 1."
    assert parse_deadline_from_text(text, today=TODAY) == date(2024, 11, 1)
