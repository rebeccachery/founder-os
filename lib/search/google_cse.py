import os

import httpx

from lib.schemas import SearchResult
from lib.search.domains import SOCIAL_HOSTS

# Google Custom Search JSON API's dateRestrict syntax: d/w/m/y + count.
_DATE_RESTRICT_BY_RANGE = {"day": "d1", "week": "w1", "month": "m1", "year": "y1"}


def search_google_cse(
    query: str,
    max_results: int = 5,
    exclude_domains: list[str] | None = None,
    time_range: str | None = None,
) -> list[SearchResult]:
    api_key = os.getenv("GOOGLE_CSE_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not api_key or not cx:
        return []

    excluded = SOCIAL_HOSTS if exclude_domains is None else exclude_domains
    if excluded:
        query = f"{query} " + " ".join(f"-site:{d}" for d in excluded)

    params: dict[str, str | int] = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(max_results, 10),
    }
    date_restrict = _DATE_RESTRICT_BY_RANGE.get(time_range or "")
    if date_restrict:
        params["dateRestrict"] = date_restrict

    response = httpx.get(
        "https://www.googleapis.com/customsearch/v1",
        params=params,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    results: list[SearchResult] = []
    for item in data.get("items", [])[:max_results]:
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="google_cse",
                raw=item,
            )
        )
    return results
