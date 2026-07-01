from dataclasses import dataclass, field
from datetime import date, timedelta

import sqlite3

from lib.db import get_deadlines, list_scout_opportunities, list_table
from lib.social.profile import load_features_config


@dataclass
class AssistantContext:
    briefing_date: date
    deadlines: list[dict] = field(default_factory=list)
    applications: list[dict] = field(default_factory=list)
    follow_ups: list[dict] = field(default_factory=list)
    launches: list[dict] = field(default_factory=list)
    meetings: list[dict] = field(default_factory=list)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def collect_assistant_context(
    conn: sqlite3.Connection,
    briefing_date: date | None = None,
) -> AssistantContext:
    today = briefing_date or date.today()
    ctx = AssistantContext(briefing_date=today)
    stale_cutoff = today - timedelta(days=30)

    ctx.deadlines = get_deadlines(conn, days=90)

    for row in list_scout_opportunities(conn, limit=200):
        if row.get("status") not in ("new", "reviewed", "applied"):
            continue
        due = _parse_date(row.get("deadline_at"))
        if due and due < stale_cutoff:
            continue
        category = row.get("category") or "scout"
        ctx.applications.append(
            {
                "title": row["name"],
                "category": category,
                "due_at": row.get("deadline_at"),
                "url": row.get("url"),
                "source_id": row["id"],
                "source_table": "scout_opportunities",
                "status": row.get("status"),
                "score_total": row.get("score_total"),
                "source": row.get("source"),
            }
        )

    for row in list_table(conn, "contacts", limit=200):
        follow_up = row.get("next_follow_up_at")
        if not follow_up:
            continue
        follow_date = _parse_date(follow_up)
        if follow_date and follow_date <= today + timedelta(days=14):
            ctx.follow_ups.append(
                {
                    "title": row["name"],
                    "category": "crm",
                    "due_at": follow_up,
                    "url": None,
                    "source_id": row["id"],
                    "status": row.get("status"),
                    "organization": row.get("organization"),
                }
            )

    features_cfg = load_features_config()
    for milestone in features_cfg.milestones:
        target = milestone.target_date
        if isinstance(target, str):
            target = _parse_date(target)
        if not target:
            continue
        if target < today - timedelta(days=7) or target > today + timedelta(days=90):
            continue
        ctx.launches.append(
            {
                "title": milestone.name,
                "category": "launch",
                "due_at": target.isoformat(),
                "url": None,
                "source_id": None,
                "status": milestone.status,
                "description": milestone.description,
            }
        )

    for feature in features_cfg.features:
        shipped = feature.shipped_at
        if isinstance(shipped, str):
            shipped = _parse_date(shipped)
        if not shipped or shipped < today or shipped > today + timedelta(days=30):
            continue
        ctx.launches.append(
            {
                "title": feature.name,
                "category": "launch",
                "due_at": shipped.isoformat(),
                "url": feature.url,
                "source_id": None,
                "status": feature.status,
                "description": feature.hook,
            }
        )

    return ctx
