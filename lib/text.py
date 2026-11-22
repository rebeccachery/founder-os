"""Keyword matching shared by the rankers.

Rankers originally used plain substring checks (``"ai" in text``), which made
short keywords fire inside unrelated words: "AI" matched "email", "said" and
"maintain", and "LLM" matched "enrollment". On the live scout corpus, about half
of all "AI" hits were false positives of this kind (see ``evals/README.md``).

``keyword_hits`` matches on word boundaries and tolerates simple plurals
("teacher" matches "teachers"), which is the matching rule every ranker uses now.
``substring_hits`` keeps the old behaviour so the evaluation harness can measure
the difference between the two.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from functools import lru_cache

Matcher = Callable[[str, Iterable[str]], int]


@lru_cache(maxsize=4096)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword.lower().strip())
    # (?<!\w) / (?!\w) instead of \b so keywords that start or end with
    # punctuation ("0 to 1", "cc-by-4.0") still anchor correctly.
    return re.compile(rf"(?<!\w){escaped}(?:s|es)?(?!\w)")


def keyword_hits(text: str, keywords: Iterable[str]) -> int:
    """Count distinct keywords that appear in ``text`` as whole words."""
    normalized = text.lower()
    return sum(1 for kw in keywords if kw.strip() and _keyword_pattern(kw).search(normalized))


def substring_hits(text: str, keywords: Iterable[str]) -> int:
    """Legacy matcher: counts keywords found anywhere, including inside other words."""
    normalized = text.lower()
    return sum(1 for kw in keywords if kw.strip() and kw.lower() in normalized)


def keyword_score(
    text: str,
    keywords: list[str],
    *,
    saturation: float = 0.15,
    matcher: Matcher = keyword_hits,
) -> float:
    """Map keyword hits to 0–100.

    The score saturates once ``saturation`` × len(keywords) distinct keywords
    match (15% by default), so a long keyword list doesn't make every
    signal look weak.
    """
    if not keywords:
        return 0.0
    hits = matcher(text, keywords)
    return min(100.0, (hits / max(len(keywords) * saturation, 1)) * 100)
