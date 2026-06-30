import os

import httpx

from lib.discovery.normalize import DiscoveryHit

GITHUB_API = "https://api.github.com"


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_github_repos(
    query: str,
    resource_type: str,
    max_results: int = 10,
) -> list[DiscoveryHit]:
    hits: list[DiscoveryHit] = []
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{GITHUB_API}/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(max_results, 30),
                },
                headers=_headers(),
            )
            response.raise_for_status()
            items = response.json().get("items", [])
    except httpx.HTTPError:
        return hits

    for repo in items[:max_results]:
        license_info = repo.get("license") or {}
        hits.append(
            DiscoveryHit(
                name=repo.get("full_name") or repo.get("name") or "unknown",
                url=repo.get("html_url") or "",
                description=repo.get("description") or "",
                resource_type=resource_type,
                source="github",
                organization=(repo.get("owner") or {}).get("login"),
                license=license_info.get("spdx_id"),
                stars=repo.get("stargazers_count"),
                task_tags=repo.get("topics") or [],
                last_updated_at=repo.get("updated_at"),
                published_at=repo.get("created_at"),
                raw={
                    "full_name": repo.get("full_name"),
                    "language": repo.get("language"),
                    "open_issues": repo.get("open_issues_count"),
                },
            )
        )
    return [hit for hit in hits if hit.url]
