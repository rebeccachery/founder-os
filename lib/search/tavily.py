import os

import httpx

from lib.schemas import SearchResult


def search_tavily(query: str, max_results: int = 5) -> list[SearchResult]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []

    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        },
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
            )
        )
    return results
