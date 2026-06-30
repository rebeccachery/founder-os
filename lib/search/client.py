import os
from pathlib import Path

import yaml

from lib.schemas import SearchResult
from lib.search.google_cse import search_google_cse
from lib.search.serpapi import search_serpapi
from lib.search.tavily import search_tavily

PROVIDERS = {
    "tavily": search_tavily,
    "serpapi": search_serpapi,
    "google_cse": search_google_cse,
}

DEFAULT_FALLBACK_ORDER = ["tavily", "serpapi", "google_cse"]


def get_fallback_order() -> list[str]:
    raw = os.getenv("SEARCH_FALLBACK_ORDER", ",".join(DEFAULT_FALLBACK_ORDER))
    return [p.strip() for p in raw.split(",") if p.strip()]


def search(
    query: str,
    provider: str | None = None,
    max_results: int = 5,
) -> list[SearchResult]:
    if provider:
        fn = PROVIDERS.get(provider)
        if fn is None:
            raise ValueError(f"Unknown search provider: {provider}")
        return fn(query, max_results=max_results)

    for name in get_fallback_order():
        fn = PROVIDERS.get(name)
        if fn is None:
            continue
        results = fn(query, max_results=max_results)
        if results:
            return results
    return []


def load_queries(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    return data.get("queries", [])
