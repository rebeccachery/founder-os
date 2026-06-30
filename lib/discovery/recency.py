from datetime import datetime

from lib.discovery.normalize import DiscoveryHit
from lib.discovery.profile import EVERGREEN_RESOURCE_TYPES, OssProfile


def parse_updated_at(last_updated_at: str | None) -> datetime | None:
    if not last_updated_at:
        return None
    try:
        updated = datetime.fromisoformat(last_updated_at.replace("Z", "+00:00"))
        if updated.tzinfo:
            return updated.replace(tzinfo=None)
        return updated
    except ValueError:
        return None


def days_since_update(last_updated_at: str | None) -> int | None:
    updated = parse_updated_at(last_updated_at)
    if updated is None:
        return None
    return (datetime.utcnow() - updated).days


def should_ingest(hit: DiscoveryHit, profile: OssProfile) -> bool:
    """Hybrid recency: hard-filter stale repos/models; keep datasets and evergreen types."""
    if hit.resource_type in EVERGREEN_RESOURCE_TYPES:
        return True
    if hit.resource_type == "dataset":
        return True

    max_days = profile.recency.hard_filter_days.get(hit.resource_type)
    if max_days is None:
        return True

    days = days_since_update(hit.last_updated_at)
    if days is None:
        return True
    return days <= max_days


def is_recent(last_updated_at: str | None, recent_days: int) -> bool:
    days = days_since_update(last_updated_at)
    if days is None:
        return False
    return days <= recent_days
