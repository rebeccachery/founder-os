from pathlib import Path

import yaml

SCOUT_CATEGORIES = (
    "accelerators",
    "fellowships",
    "grants",
    "startup_competitions",
    "hackathons",
    "cloud_credits",
    "university_programs",
    "ai_research_funding",
    "pitch_competitions",
)


def _load_categories_from_file(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    categories = data.get("categories", {})
    return {
        category: [q for q in queries if isinstance(q, str) and q.strip()]
        for category, queries in categories.items()
        if isinstance(queries, list)
    }


def load_categorized_queries(
    path: Path,
    merge_path: Path | None = None,
) -> dict[str, list[str]]:
    merged = _load_categories_from_file(path)
    if merge_path is not None:
        for category, queries in _load_categories_from_file(merge_path).items():
            merged.setdefault(category, []).extend(queries)
    return merged
