"""Ranking systems under evaluation. Each maps candidates → scores (higher = better).

The keyword systems are successive versions of ``lib.scout.ranker``:

* ``keyword_v1`` — the original: substring keyword matching
* ``keyword_v2`` — whole-word matching (``lib.text.keyword_hits``)
* ``keyword_v3`` — v2 + title actionability penalty (``lib.scout.actionability``); production

The rest are baselines a ranker has to beat to justify its complexity.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from collections.abc import Callable
from datetime import date

from evals.dataset import Candidate
from lib.scout.profile import FounderProfile
from lib.scout.ranker import _deadline_score, rank_opportunity
from lib.text import Matcher, keyword_hits, substring_hits

System = Callable[[list[Candidate], FounderProfile, date], list[float]]


def _keyword_system(*, matcher: Matcher, actionability: bool) -> System:
    def system(cands: list[Candidate], profile: FounderProfile, today: date) -> list[float]:
        return [
            rank_opportunity(
                title=c.title,
                snippet=c.snippet,
                category=c.category,
                deadline_at=c.deadline_at,
                profile=profile,
                today=today,
                matcher=matcher,
                actionability=actionability,
            ).scores.total
            for c in cands
        ]

    return system


keyword_v3 = _keyword_system(matcher=keyword_hits, actionability=True)  # production
keyword_v2 = _keyword_system(matcher=keyword_hits, actionability=False)
keyword_v1 = _keyword_system(matcher=substring_hits, actionability=False)  # original


def deadline_only(cands: list[Candidate], profile: FounderProfile, today: date) -> list[float]:
    return [_deadline_score(c.deadline_at, today) for c in cands]


def random_baseline(cands: list[Candidate], profile: FounderProfile, today: date) -> list[float]:
    rng = random.Random(42)
    return [rng.random() for _ in cands]


_TOKEN = re.compile(r"[a-z0-9][a-z0-9\-]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def bm25(cands: list[Candidate], profile: FounderProfile, today: date) -> list[float]:
    """Okapi BM25 with the founder profile (description + all keywords) as the query.

    The standard lexical-retrieval baseline: no hand-set weights, just term
    statistics over this candidate pool.
    """
    signals = profile.signals
    query_text = " ".join(
        [
            profile.company.description,
            *signals.ai_keywords,
            *signals.education_keywords,
            *signals.language_preservation_keywords,
            *signals.minority_founder_keywords,
            *signals.stage_keywords.get(profile.company.stage, []),
        ]
    )
    query = set(_tokens(query_text))
    docs = [_tokens(c.text) for c in cands]
    n = len(docs)
    avgdl = sum(map(len, docs)) / n if n else 0.0
    df = Counter(term for doc in docs for term in set(doc))
    k1, b = 1.5, 0.75
    scores = []
    for doc in docs:
        tf = Counter(doc)
        score = 0.0
        for term in query:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * len(doc) / (avgdl or 1))
            score += idf * tf[term] * (k1 + 1) / denom
        scores.append(score)
    return scores


SYSTEMS: dict[str, System] = {
    "keyword_v3 (production)": keyword_v3,
    "keyword_v2 (word match)": keyword_v2,
    "keyword_v1 (substring)": keyword_v1,
    "bm25 (profile query)": bm25,
    "deadline_only": deadline_only,
    "random": random_baseline,
}
