from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveryHit:
    name: str
    url: str
    resource_type: str
    source: str
    description: str = ""
    organization: str | None = None
    license: str | None = None
    stars: int | None = None
    task_tags: list[str] = field(default_factory=list)
    language_tags: list[str] = field(default_factory=list)
    metrics_json: dict[str, Any] | None = None
    published_at: str | None = None
    last_updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def dedupe_hits(hits: list[DiscoveryHit]) -> list[DiscoveryHit]:
    seen: set[str] = set()
    unique: list[DiscoveryHit] = []
    for hit in hits:
        if hit.url and hit.url not in seen:
            seen.add(hit.url)
            unique.append(hit)
    return unique
