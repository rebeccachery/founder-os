from datetime import date
from pathlib import Path
from typing import Any

import yaml

from lib.scout.profile import FounderProfile, load_founder_profile

SCOUT_CATEGORIES = (
    "accelerators",
    "founder_in_residence",
    "fellowships",
    "grants",
    "startup_competitions",
    "hackathons",
    "cloud_credits",
    "university_programs",
    "ai_research_funding",
    "pitch_competitions",
)

# Which founder-profile signal-keyword pools feed niche query generation, and
# in what order. Each contributes at most one query per category per run.
# Override with `niche_keyword_pools:` in queries.yaml. Eligibility keywords
# ("Black founders", "women founders") come first: programs restricted to a
# founder group are the highest-yield niche searches.
NICHE_KEYWORD_POOLS = ("minority_founder_keywords", "language_preservation_keywords", "ai_keywords")


def _load_raw_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _load_categories_from_file(path: Path) -> dict[str, list[str]]:
    data = _load_raw_yaml(path)
    categories = data.get("categories", {})
    return {
        category: [q for q in queries if isinstance(q, str) and q.strip()]
        for category, queries in categories.items()
        if isinstance(queries, list)
    }


def _render_year_templates(queries: list[str], today: date) -> list[str]:
    year = today.year
    next_year = year + 1
    rendered = []
    for q in queries:
        try:
            rendered.append(q.format(year=year, next_year=next_year))
        except (KeyError, IndexError):
            rendered.append(q)  # tolerate stray braces in a hand-written query
    return rendered


def _pick_keyword(pool: list[str], seed: int) -> str | None:
    if not pool:
        return None
    return pool[seed % len(pool)]


def _generate_niche_queries(
    config: dict[str, Any],
    profile: FounderProfile,
    today: date,
) -> dict[str, list[str]]:
    """Combine each category's short intent phrase with a founder-profile
    keyword, so the search itself is niche-targeted instead of generic-then-
    filtered. E.g. "startup accelerator" + "underresourced language" instead
    of just "startup accelerator application open".

    Deterministic but rotates day-to-day (seeded by day-of-year) so repeated
    runs don't always draw the same keyword from a pool forever.
    """
    phrases: dict[str, str] = config.get("category_phrases", {}) or {}
    if not phrases:
        return {}

    pools = config.get("niche_keyword_pools") or NICHE_KEYWORD_POOLS
    day_seed = today.timetuple().tm_yday
    year = today.year
    niche: dict[str, list[str]] = {}
    for category, phrase in phrases.items():
        if not isinstance(phrase, str) or not phrase.strip():
            continue
        queries: list[str] = []
        for i, pool_name in enumerate(pools):
            pool = getattr(profile.signals, pool_name, None) or []
            keyword = _pick_keyword(list(pool), day_seed + i)
            if keyword:
                queries.append(f"{phrase} {year} {keyword}")
        if queries:
            niche[category] = queries
    return niche


def load_categorized_queries(
    path: Path,
    merge_path: Path | None = None,
    profile: FounderProfile | None = None,
    today: date | None = None,
) -> dict[str, list[str]]:
    """Public queries + private overrides + profile-generated niche queries, per category.

    The private override file (``private/agents/funding_scout/queries.yaml``) can:

    * add queries under ``categories:`` (merged with the public ones)
    * set ``disabled_categories: [hackathons, ...]`` to skip a category entirely
    * set ``niche_keyword_pools:`` to choose which profile keyword lists drive niche queries
    """
    today = today or date.today()
    config = _load_raw_yaml(path)
    override = _load_raw_yaml(merge_path) if merge_path is not None else {}
    if override.get("niche_keyword_pools"):
        config = {**config, "niche_keyword_pools": override["niche_keyword_pools"]}
    disabled = set(override.get("disabled_categories") or []) | set(config.get("disabled_categories") or [])

    merged = _load_categories_from_file(path)
    if merge_path is not None:
        for category, queries in _load_categories_from_file(merge_path).items():
            merged.setdefault(category, []).extend(queries)

    merged = {cat: _render_year_templates(qs, today) for cat, qs in merged.items()}

    profile = profile or load_founder_profile()
    for category, niche_queries in _generate_niche_queries(config, profile, today).items():
        merged.setdefault(category, []).extend(niche_queries)

    return {cat: list(dict.fromkeys(qs)) for cat, qs in merged.items() if cat not in disabled}


def load_category_time_ranges(path: Path) -> dict[str, str]:
    """Optional per-category Tavily/search time_range hint ("day"/"week"/
    "month"/"year"). Categories without an entry search with no recency bias.
    """
    data = _load_raw_yaml(path)
    raw = data.get("category_time_range", {}) or {}
    valid = {"day", "week", "month", "year"}
    return {k: v for k, v in raw.items() if isinstance(v, str) and v in valid}
