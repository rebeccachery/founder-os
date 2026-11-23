from datetime import date

from lib.opportunities.intake import infer_category
from lib.scout.profile import FounderProfile, SignalKeywords
from lib.scout.queries import load_categorized_queries

PUBLIC = """
categories:
  grants: ["startup grant {year}"]
  hackathons: ["hackathon {year}"]
category_phrases:
  grants: "startup grant"
  hackathons: "startup hackathon"
"""

PROFILE = FounderProfile(
    signals=SignalKeywords(
        minority_founder_keywords=["Black founders"],
        education_keywords=["EdTech"],
        ai_keywords=["speech AI"],
    )
)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_private_override_merges_disables_and_dedupes(tmp_path):
    public = _write(tmp_path, "public.yaml", PUBLIC)
    private = _write(
        tmp_path,
        "private.yaml",
        'disabled_categories: [hackathons]\ncategories:\n  grants: ["startup grant {year}", "grant for Black founders"]\n',
    )
    queries = load_categorized_queries(public, private, PROFILE, date(2026, 11, 22))
    assert "hackathons" not in queries
    assert queries["grants"].count("startup grant 2026") == 1
    assert "grant for Black founders" in queries["grants"]


def test_niche_pools_default_to_eligibility_not_education(tmp_path):
    public = _write(tmp_path, "public.yaml", PUBLIC)
    grants = load_categorized_queries(public, None, PROFILE, date(2026, 11, 22))["grants"]
    assert "startup grant 2026 Black founders" in grants
    assert not any("EdTech" in q for q in grants)


def test_niche_pools_configurable_from_override(tmp_path):
    public = _write(tmp_path, "public.yaml", PUBLIC)
    private = _write(tmp_path, "private.yaml", "niche_keyword_pools: [education_keywords]\n")
    grants = load_categorized_queries(public, private, PROFILE, date(2026, 11, 22))["grants"]
    assert "startup grant 2026 EdTech" in grants
    assert not any("Black founders" in q for q in grants)


def test_founder_in_residence_category_inferred_first():
    text = "Entrepreneur in Residence fellowship for AI founders"
    assert infer_category(text) == "founder_in_residence"
