import pytest

from lib.text import keyword_hits, keyword_score, substring_hits


@pytest.mark.parametrize(
    ("text", "keyword"),
    [
        ("Send us an email to apply", "AI"),
        ("She said the maintainers agreed", "AI"),
        ("Open enrollment for the cohort", "LLM"),
        ("HTML templates for landing pages", "ML"),
    ],
)
def test_short_keywords_do_not_match_inside_words(text, keyword):
    # Regression: the original substring matcher counted all of these as hits.
    assert substring_hits(text, [keyword]) == 1
    assert keyword_hits(text, [keyword]) == 0


@pytest.mark.parametrize(
    ("text", "keyword"),
    [
        ("Grants for AI startups", "AI"),
        ("AI-powered tutoring", "AI"),
        ("Support for teachers and students", "teacher"),
        ("Two new classes", "class"),
        ("Join us — pre-seed founders welcome", "pre-seed"),
        ("from 0 to 1, fast", "0 to 1"),
    ],
)
def test_whole_words_plurals_and_punctuated_keywords_match(text, keyword):
    assert keyword_hits(text, [keyword]) == 1


def test_matching_is_case_insensitive_and_counts_distinct_keywords():
    assert keyword_hits("NLP and nlp and Machine Learning", ["nlp", "machine learning", "asr"]) == 2


def test_keyword_score_saturates_at_100():
    keywords = [f"kw{i}" for i in range(20)]
    text = " ".join(keywords[:3])  # 3 hits = 15% of 20 → saturation
    assert keyword_score(text, keywords) == 100.0
    assert keyword_score("nothing", keywords) == 0.0
    assert keyword_score("anything", []) == 0.0
