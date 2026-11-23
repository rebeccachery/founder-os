import os

import httpx

from lib.schemas import SearchResult
from lib.search.domains import SOCIAL_HOSTS

# Tavily's own vocabulary: "day" | "week" | "month" | "year".
TIME_RANGE_VALUES = ("day", "week", "month", "year")


def search_tavily(
    query: str,
    max_results: int = 5,
    exclude_domains: list[str] | None = None,
    time_range: str | None = None,
) -> list[SearchResult]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []

    payload: dict = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "include_answer": False,
    }
    excluded = SOCIAL_HOSTS if exclude_domains is None else exclude_domains
    if excluded:
        payload["exclude_domains"] = list(excluded)
    if time_range in TIME_RANGE_VALUES:
        payload["time_range"] = time_range

    response = httpx.post(
        "https://api.tavily.com/search",
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    results: list[SearchResult] = []
    for item in data.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source="tavily",
                raw=item,
                source_relevance=item.get("score"),
            )
        )
    return results
