import os

import httpx

from lib.schemas import SearchResult
from lib.search.domains import SOCIAL_HOSTS

# Google's standard date-range search operator (via SerpAPI's `tbs` passthrough).
_TBS_BY_RANGE = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}


def search_serpapi(
    query: str,
    max_results: int = 5,
    exclude_domains: list[str] | None = None,
    time_range: str | None = None,
) -> list[SearchResult]:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []

    excluded = SOCIAL_HOSTS if exclude_domains is None else exclude_domains
    if excluded:
        query = f"{query} " + " ".join(f"-site:{d}" for d in excluded)

    params: dict[str, str | int] = {
        "q": query,
        "api_key": api_key,
        "num": max_results,
    }
    tbs = _TBS_BY_RANGE.get(time_range or "")
    if tbs:
        params["tbs"] = tbs

    response = httpx.get(
        "https://serpapi.com/search.json",
        params=params,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    results: list[SearchResult] = []
    for item in data.get("organic_results", [])[:max_results]:
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="serpapi",
                raw=item,
            )
        )
    return results
