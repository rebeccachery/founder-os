import math
import re
from dataclasses import dataclass
from datetime import datetime

from lib.discovery.normalize import DiscoveryHit
from lib.discovery.profile import OssProfile
from lib.schemas import OssScores


@dataclass
class RankedOssResource:
    scores: OssScores
    rank_reason: str
    target_language_match: bool = False


def _normalize(text: str) -> str:
    return text.lower()


def _keyword_score(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    normalized = _normalize(text)
    hits = sum(1 for kw in keywords if _normalize(kw) in normalized)
    return min(100.0, (hits / max(len(keywords) * 0.15, 1)) * 100)


def _target_language_score(text: str, tags: list[str], profile: OssProfile) -> tuple[float, bool]:
    codes = profile.signals.target_language_codes
    names = profile.signals.target_language_names
    if not codes and not names:
        return 0.0, False

    combined = _normalize(f"{text} {' '.join(tags)}")
    hits = 0
    total = 0

    for code in codes:
        total += 1
        if re.search(rf"\b{re.escape(_normalize(code))}\b", combined):
            hits += 1

    for name in names:
        total += 1
        if _normalize(name) in combined:
            hits += 1

    if total == 0:
        return 0.0, False

    score = min(100.0, (hits / max(total * 0.4, 1)) * 100)
    return score, hits > 0


def _language_fit_score(text: str, tags: list[str], profile: OssProfile) -> tuple[float, bool]:
    generic = _keyword_score(text, profile.signals.language_keywords)
    target, matched = _target_language_score(text, tags, profile)
    if target > 0:
        return round(min(100.0, generic * 0.35 + target * 0.65), 1), matched
    return generic, False


def _recency_score(last_updated_at: str | None) -> float:
    if not last_updated_at:
        return 20.0
    try:
        updated = datetime.fromisoformat(last_updated_at.replace("Z", "+00:00"))
        if updated.tzinfo:
            updated = updated.replace(tzinfo=None)
        days_ago = (datetime.utcnow() - updated).days
    except ValueError:
        return 20.0

    if days_ago <= 30:
        return 100.0
    if days_ago <= 90:
        return 80.0
    if days_ago <= 180:
        return 60.0
    if days_ago <= 365:
        return 40.0
    return 20.0


def _popularity_score(stars: int | None) -> float:
    if stars is None or stars <= 0:
        return 10.0
    return min(100.0, math.log10(stars + 1) * 25)


def _license_score(license_name: str | None, preferred: list[str]) -> float:
    if not license_name:
        return 30.0
    normalized = _normalize(license_name)
    for pref in preferred:
        if _normalize(pref) in normalized:
            return 100.0
    if "open" in normalized or "cc-" in normalized:
        return 70.0
    return 20.0


def _build_reason(
    scores: OssScores,
    resource_type: str,
    *,
    target_language_match: bool,
) -> str:
    highlights: list[str] = []
    if target_language_match:
        highlights.append("Haitian Creole match")
    if scores.task_fit >= 50:
        highlights.append("task fit")
    if scores.language_fit >= 50 and not target_language_match:
        highlights.append("language fit")
    if scores.recency >= 70:
        highlights.append("recently updated")
    if scores.popularity >= 50:
        highlights.append("popular")
    if scores.license_fit >= 70:
        highlights.append("permissive license")

    label = resource_type.replace("_", " ")
    if highlights:
        return f"Strong {' + '.join(highlights[:3])} ({label})"
    return f"Moderate match ({label})"


def rank_oss_resource(hit: DiscoveryHit, profile: OssProfile) -> RankedOssResource:
    text = " ".join(
        filter(
            None,
            [
                hit.name,
                hit.description,
                hit.organization or "",
                " ".join(hit.task_tags),
                " ".join(hit.language_tags),
            ],
        )
    )
    signals = profile.signals
    priorities = profile.priorities

    language_fit, target_match = _language_fit_score(text, hit.task_tags + hit.language_tags, profile)

    scores = OssScores(
        task_fit=_keyword_score(text, signals.task_keywords),
        language_fit=language_fit,
        recency=_recency_score(hit.last_updated_at),
        popularity=_popularity_score(hit.stars),
        license_fit=_license_score(hit.license, signals.license_preferred),
    )
    scores.total = round(
        scores.task_fit * priorities.task_fit
        + scores.language_fit * priorities.language_fit
        + scores.recency * priorities.recency
        + scores.popularity * priorities.popularity
        + scores.license_fit * priorities.license_fit,
        1,
    )

    return RankedOssResource(
        scores=scores,
        rank_reason=_build_reason(scores, hit.resource_type, target_language_match=target_match),
        target_language_match=target_match,
    )
