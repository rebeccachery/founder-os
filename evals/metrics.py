"""Ranking metrics. Pure Python so the eval runs anywhere CI does.

All functions take ``ranked_labels``: the graded relevance labels (0, 1, 2) of
candidates in the order a system ranked them, best first.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

RELEVANT_AT = 1  # label >= 1 ("worth a look") counts as relevant for binary metrics


def _binary(labels: Sequence[int]) -> list[int]:
    return [1 if label >= RELEVANT_AT else 0 for label in labels]


def precision_at_k(ranked_labels: Sequence[int], k: int) -> float:
    top = _binary(ranked_labels[:k])
    return sum(top) / k if k else 0.0


def recall_at_k(ranked_labels: Sequence[int], k: int) -> float:
    rel = _binary(ranked_labels)
    total = sum(rel)
    return sum(rel[:k]) / total if total else 0.0


def dcg_at_k(ranked_labels: Sequence[int], k: int) -> float:
    return sum((2**label - 1) / math.log2(i + 2) for i, label in enumerate(ranked_labels[:k]))


def ndcg_at_k(ranked_labels: Sequence[int], k: int) -> float:
    ideal = dcg_at_k(sorted(ranked_labels, reverse=True), k)
    return dcg_at_k(ranked_labels, k) / ideal if ideal else 0.0


def average_precision(ranked_labels: Sequence[int]) -> float:
    rel = _binary(ranked_labels)
    hits, total = 0, 0.0
    for i, r in enumerate(rel, start=1):
        if r:
            hits += 1
            total += hits / i
    return total / hits if hits else 0.0


def roc_auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Probability a random relevant item outscores a random non-relevant one (ties = 0.5)."""
    pos = [s for s, y in zip(scores, _binary(labels), strict=True) if y]
    neg = [s for s, y in zip(scores, _binary(labels), strict=True) if not y]
    if not pos or not neg:
        return float("nan")
    # O(n log n) via ranks instead of the O(n²) pairwise loop.
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for idx in order[i : j + 1]:
            ranks[idx] = avg_rank
        i = j + 1
    binary = _binary(labels)
    pos_rank_sum = sum(r for r, y in zip(ranks, binary, strict=True) if y)
    n_pos, n_neg = len(pos), len(neg)
    return (pos_rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def bootstrap_ci(
    scores: Sequence[float],
    labels: Sequence[int],
    metric: Callable[[Sequence[float], Sequence[int]], float],
    *,
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI over candidates (resample items with replacement)."""
    rng = random.Random(seed)
    n = len(scores)
    samples: list[float] = []
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        value = metric([scores[i] for i in idx], [labels[i] for i in idx])
        if not math.isnan(value):
            samples.append(value)
    if not samples:
        return (float("nan"), float("nan"))
    samples.sort()
    lo = samples[int(alpha / 2 * len(samples))]
    hi = samples[min(len(samples) - 1, int((1 - alpha / 2) * len(samples)))]
    return lo, hi


def rank_by(scores: Sequence[float], labels: Sequence[int]) -> list[int]:
    """Labels reordered by descending score. Stable, so ties keep input order."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    return [labels[i] for i in order]


def paired_bootstrap(
    scores_a: Sequence[float],
    scores_b: Sequence[float],
    labels: Sequence[int],
    metric: Callable[[Sequence[float], Sequence[int]], float],
    *,
    n_resamples: int = 1000,
    seed: int = 0,
) -> tuple[float, tuple[float, float], float]:
    """Difference metric(A) − metric(B) on the same resampled items each round.

    Returns (observed delta, 95% CI of delta, share of resamples where A > B).
    Pairing matters: two systems' individual CIs can overlap even when A beats
    B on nearly every resample of the same data.
    """
    rng = random.Random(seed)
    n = len(labels)
    observed = metric(scores_a, labels) - metric(scores_b, labels)
    deltas: list[float] = []
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        y = [labels[i] for i in idx]
        if not any(label >= RELEVANT_AT for label in y):
            continue
        deltas.append(metric([scores_a[i] for i in idx], y) - metric([scores_b[i] for i in idx], y))
    deltas.sort()
    lo = deltas[int(0.025 * len(deltas))]
    hi = deltas[min(len(deltas) - 1, int(0.975 * len(deltas)))]
    return observed, (lo, hi), sum(d > 0 for d in deltas) / len(deltas)
