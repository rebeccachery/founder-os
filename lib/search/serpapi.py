import os

import httpx

from lib.schemas import SearchResult


def search_serpapi(query: str, max_results: int = 5) -> list[SearchResult]:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []

    response = httpx.get(
        "https://serpapi.com/search.json",
        params={
            "q": query,
            "api_key": api_key,
            "num": max_results,
        },
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
