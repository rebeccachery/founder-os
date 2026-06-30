import os

import httpx

from lib.schemas import SearchResult


def search_google_cse(query: str, max_results: int = 5) -> list[SearchResult]:
    api_key = os.getenv("GOOGLE_CSE_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not api_key or not cx:
        return []

    response = httpx.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": min(max_results, 10),
        },
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
