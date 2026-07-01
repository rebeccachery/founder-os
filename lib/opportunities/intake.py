import json
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

import sqlite3

from lib.db import upsert_by_url
from lib.schemas import SavedOpportunityCreate
from lib.scout.profile import load_founder_profile
from lib.scout.ranker import parse_deadline_from_text, rank_opportunity

SCOUT_CATEGORIES = (
    "accelerators",
    "fellowships",
    "grants",
    "startup_competitions",
    "hackathons",
    "cloud_credits",
    "university_programs",
    "ai_research_funding",
    "other",
)

CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("fellowships", ("fellowship", "fellow", "cohort program")),
    ("grants", ("grant", "sbir", "funding opportunity", "rfp")),
    ("startup_competitions", ("competition", "pitch", "prize", "challenge")),
    ("accelerators", ("accelerator", "incubator", "batch")),
    ("hackathons", ("hackathon", "hack day")),
    ("cloud_credits", ("cloud credits", "aws activate", "gcp credits", "azure credits")),
    ("university_programs", ("university", "campus", "berkeley", "stanford")),
    ("ai_research_funding", ("research funding", "nlp grant", "ai grant")),
]

SOCIAL_HOSTS = ("twitter.com", "x.com", "t.co", "mobile.twitter.com")

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL — include https://")

    clean_query = []
    for key, values in parse_qs(parsed.query, keep_blank_values=False).items():
        if key.lower().startswith("utm_") or key.lower() in ("fbclid", "gclid"):
            continue
        clean_query.extend(f"{key}={value}" for value in values)

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            parsed.params,
            "&".join(clean_query) if clean_query else "",
            "",
        )
    )


def _is_social_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == h or host.endswith(f".{h}") for h in SOCIAL_HOSTS)


def extract_urls_from_text(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in URL_PATTERN.findall(text):
        url = match.rstrip(".,)")
        try:
            normalized = normalize_url(url)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        found.append(normalized)
    return found


def pick_application_url(text: str, explicit_url: str | None) -> str:
    if explicit_url:
        return normalize_url(explicit_url)

    urls = extract_urls_from_text(text)
    if not urls:
        raise ValueError("No URL found — paste an application link or tweet text with a link.")

    non_social = [u for u in urls if not _is_social_url(u)]
    if non_social:
        return non_social[0]
    return urls[0]


def infer_category(text: str) -> str:
    normalized = text.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "other"


def derive_name(text: str, url: str, name: str | None) -> str:
    if name and name.strip():
        return name.strip()[:200]

    for line in text.splitlines():
        cleaned = line.strip().lstrip("-•*").strip()
        if cleaned and not cleaned.startswith("http") and len(cleaned) > 8:
            return cleaned[:200]

    host = urlparse(url).netloc.removeprefix("www.")
    slug = urlparse(url).path.strip("/").split("/")[-1]
    if slug and slug not in ("apply", "application"):
        return f"{slug.replace('-', ' ').title()} ({host})"[:200]
    return host[:200]


def _resolve_source(payload: SavedOpportunityCreate) -> str:
    if payload.source_tweet_url:
        return "twitter"
    return "manual"


def save_opportunity(
    conn: sqlite3.Connection,
    payload: SavedOpportunityCreate,
) -> dict[str, Any]:
    combined_text = " ".join(
        filter(None, [payload.description or "", payload.name or "", payload.url or ""])
    )
    url = pick_application_url(combined_text, payload.url)
    name = derive_name(combined_text, url, payload.name)
    category = payload.category or infer_category(combined_text)
    if category not in SCOUT_CATEGORIES:
        category = "other"

    deadline_at = payload.deadline_at
    if deadline_at is None and payload.description:
        deadline_at = parse_deadline_from_text(payload.description)

    profile = load_founder_profile()
    ranked = rank_opportunity(
        title=name,
        snippet=payload.description or "",
        description=payload.description,
        category=category,
        deadline_at=deadline_at,
        profile=profile,
    )

    source = _resolve_source(payload)
    raw_json: dict[str, Any] = {
        "intake": source,
        "saved_at": datetime.utcnow().isoformat(),
    }
    if payload.description:
        raw_json["original_text"] = payload.description[:2000]
    if payload.source_tweet_url:
        raw_json["source_tweet_url"] = payload.source_tweet_url
    if payload.shared_by:
        raw_json["shared_by"] = payload.shared_by

    existing = conn.execute(
        "SELECT id FROM scout_opportunities WHERE url = ?", (url,)
    ).fetchone()
    created = existing is None

    row = {
        "name": name,
        "category": category,
        "organization": payload.shared_by,
        "amount": None,
        "stage": profile.company.stage,
        "description": (payload.description or "")[:500] or None,
        "url": url,
        "deadline_at": deadline_at.isoformat() if deadline_at else None,
        "status": "new",
        "source": source,
        "score_total": ranked.scores.total,
        "score_stage_fit": ranked.scores.stage_fit,
        "score_ai_focus": ranked.scores.ai_focus,
        "score_education": ranked.scores.education_focus,
        "score_language_preservation": ranked.scores.language_preservation,
        "score_minority_founder": ranked.scores.minority_founder,
        "score_deadline": ranked.scores.deadline,
        "rank_reason": ranked.rank_reason,
        "raw_json": raw_json,
    }
    row_id = upsert_by_url(conn, "scout_opportunities", row)
    saved = conn.execute(
        "SELECT * FROM scout_opportunities WHERE id = ?", (row_id,)
    ).fetchone()

    result = dict(saved)
    result["created"] = created
    if result.get("raw_json") and isinstance(result["raw_json"], str):
        result["raw_json"] = json.loads(result["raw_json"])
    return result
