from lib.discovery.normalize import DiscoveryHit
from lib.search.client import search


def search_web(query: str, resource_type: str, max_results: int = 5) -> list[DiscoveryHit]:
    hits: list[DiscoveryHit] = []
    try:
        results = search(query, max_results=max_results)
    except Exception:
        return hits
    for result in results:
        if not result.url:
            continue
        hits.append(
            DiscoveryHit(
                name=result.title[:200],
                url=result.url,
                description=result.snippet[:500] if result.snippet else "",
                resource_type=resource_type,
                source=result.source or "web",
                raw=result.raw,
            )
        )
    return hits
