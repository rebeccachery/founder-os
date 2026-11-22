"""Is this search hit an opportunity you can apply to, or a page *about* opportunities?

Error analysis on the live corpus (``evals/README.md``) found that the
keyword ranker's top results were dominated by pages that are topically perfect
but not actionable: listicles ("Top 26 Language Learning Startups to Watch"),
press releases ("… Announces 2014 Class") and stale cycles (a title naming only
past years). None of the 40 curated opportunities matched these patterns; 14%
of raw search hits did.

The fix is a multiplicative penalty on the title only — snippets mention past
years and "how to apply" legitimately, so they're too noisy to act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_LISTICLE = re.compile(
    r"\b(?:top|best)\s+\d+\b|\b\d+\s+(?:top|best)\b|\bto watch\b|\blist of\b|\bhow to\b"
    r"|\bguide\b|\bwhat is\b|\bvs\.?\s|\brankings?\b|\bdirectory\b",
    re.IGNORECASE,
)
_NEWS = re.compile(
    r"\b(?:announces|announced|launches|launched|unveils|names|selects|welcomes)\b", re.IGNORECASE
)
_YEAR = re.compile(r"\b(20\d{2})\b")

LISTICLE_FACTOR = 0.6
NEWS_FACTOR = 0.7
STALE_FACTOR = 0.6


@dataclass(frozen=True)
class Actionability:
    multiplier: float
    flags: tuple[str, ...]


def assess_title(title: str, today: date | None = None) -> Actionability:
    today = today or date.today()
    multiplier, flags = 1.0, []
    if _LISTICLE.search(title):
        multiplier *= LISTICLE_FACTOR
        flags.append("listicle")
    if _NEWS.search(title):
        multiplier *= NEWS_FACTOR
        flags.append("news")
    years = [int(y) for y in _YEAR.findall(title)]
    if years and max(years) < today.year:
        multiplier *= STALE_FACTOR
        flags.append("past cycle")
    return Actionability(multiplier=multiplier, flags=tuple(flags))
