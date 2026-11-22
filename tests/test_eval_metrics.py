import math

import pytest

from evals.metrics import (
    average_precision,
    bootstrap_ci,
    ndcg_at_k,
    paired_bootstrap,
    precision_at_k,
    rank_by,
    recall_at_k,
    roc_auc,
)


def test_precision_recall():
    ranked = [2, 0, 1, 0, 0]
    assert precision_at_k(ranked, 2) == 0.5
    assert recall_at_k(ranked, 3) == 1.0
    assert recall_at_k([0, 0], 2) == 0.0


def test_ndcg_perfect_and_reversed():
    assert ndcg_at_k([2, 1, 0], 3) == pytest.approx(1.0)
    assert ndcg_at_k([0, 1, 2], 3) < 0.6
    assert ndcg_at_k([0, 0], 2) == 0.0


def test_average_precision_hand_computed():
    # relevant at ranks 1 and 3 → (1/1 + 2/3) / 2
    assert average_precision([1, 0, 1, 0]) == pytest.approx((1 + 2 / 3) / 2)


def test_auc_matches_pairwise_definition_with_ties():
    scores = [0.9, 0.5, 0.5, 0.1, 0.5]
    labels = [1, 1, 0, 0, 0]
    items = list(zip(scores, labels, strict=True))
    pairs = [(s_p, s_n) for s_p, y_p in items if y_p for s_n, y_n in items if not y_n]
    expected = sum(1.0 if a > b else 0.5 if a == b else 0.0 for a, b in pairs) / len(pairs)
    assert roc_auc(scores, labels) == pytest.approx(expected)
    assert math.isnan(roc_auc([1, 2], [0, 0]))


def test_rank_by_is_descending_and_stable():
    assert rank_by([0.1, 0.9, 0.9], [0, 1, 2]) == [1, 2, 0]


def test_bootstrap_ci_brackets_point_estimate():
    scores = [i / 50 for i in range(50)]
    labels = [1 if i > 35 else 0 for i in range(50)]
    lo, hi = bootstrap_ci(scores, labels, roc_auc, n_resamples=200)
    assert lo <= roc_auc(scores, labels) <= hi


def test_paired_bootstrap_detects_strictly_better_system():
    labels = [1 if i % 5 == 0 else 0 for i in range(100)]
    perfect = [float(y) for y in labels]
    noise = [((i * 37) % 100) / 100 for i in range(100)]

    def metric(s, y):
        return average_precision(rank_by(s, y))

    delta, (lo, _hi), p_better = paired_bootstrap(perfect, noise, labels, metric, n_resamples=200)
    assert delta > 0 and lo > 0 and p_better == 1.0
