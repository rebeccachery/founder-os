from datetime import date, datetime, timedelta

import sqlite3

from lib.assistant.collector import collect_assistant_context
from lib.assistant.conflicts import detect_conflicts
from lib.assistant.ranker import item_to_briefing, rank_priorities
from lib.db import list_application_drafts_bulk, list_assistant_tracks_map
from lib.schemas import BriefingItem, ExecutiveBriefing


def _enrich_with_track(item: dict, tracks: dict[int, dict]) -> dict:
    sid = item.get("source_id")
    track = tracks.get(int(sid)) if sid is not None else None
    if track:
        item = {
            **item,
            "pin_priority": track.get("pin_priority", False),
            "tracked_application": track.get("track_application", False),
        }
    else:
        item.setdefault("pin_priority", False)
        item.setdefault("tracked_application", False)
    return item


def build_briefing(
    conn: sqlite3.Connection,
    briefing_date: date | None = None,
) -> ExecutiveBriefing:
    today = briefing_date or date.today()
    ctx = collect_assistant_context(conn, today)
    tracks = list_assistant_tracks_map(conn)

    priorities = rank_priorities(ctx, tracks)
    conflicts = detect_conflicts(ctx)

    follow_ups = [
        item_to_briefing(f, today)
        for f in sorted(ctx.follow_ups, key=lambda x: x.get("due_at") or "")
    ]

    deadlines = [
        BriefingItem(
            title=row["title"],
            category=row.get("category", "deadline").replace("scout:", ""),
            due_at=row.get("deadline_at"),
            priority_score=item_to_briefing(
                {
                    "title": row["title"],
                    "category": row.get("category", ""),
                    "due_at": row.get("deadline_at"),
                    "status": row.get("status"),
                },
                today,
            ).priority_score,
            reason=item_to_briefing(
                {
                    "title": row["title"],
                    "category": row.get("category", ""),
                    "due_at": row.get("deadline_at"),
                    "status": row.get("status"),
                },
                today,
            ).reason,
            url=row.get("url"),
            source_id=row.get("source_id"),
            source_table=row.get("source_table"),
            status=row.get("status"),
        )
        for row in ctx.deadlines
        if (row.get("deadline_at") or "") <= (today + timedelta(days=14)).isoformat()
    ]

    meetings = [item_to_briefing(m, today) for m in ctx.meetings]

    draft_keys = [
        (a["source_table"], a["source_id"])
        for a in ctx.applications
        if a.get("source_table") and a.get("source_id") is not None
    ]
    draft_bodies = list_application_drafts_bulk(conn, draft_keys)

    applications: list[BriefingItem] = []
    for app in ctx.applications:
        enriched = _enrich_with_track(app, tracks)
        key = (enriched.get("source_table"), enriched.get("source_id"))
        body = draft_bodies.get((key[0], key[1])) if key[0] and key[1] is not None else None
        has_draft = bool(body)
        is_tracked = bool(enriched.get("tracked_application"))

        if not is_tracked and not has_draft:
            continue

        item = item_to_briefing(enriched, today)
        if has_draft and body:
            preview = body[:120] + ("…" if len(body) > 120 else "")
            item = item.model_copy(update={"has_draft": True, "draft_preview": preview})
        item = item.model_copy(update={"tracked_application": is_tracked})
        applications.append(item)

    applications.sort(key=lambda i: (-i.priority_score, i.due_at or "9999"))

    for launch in ctx.launches:
        launch_item = item_to_briefing(launch, today)
        if launch_item.due_at and launch_item.due_at <= (today + timedelta(days=7)).isoformat():
            if not any(d.title == launch_item.title for d in deadlines):
                deadlines.append(launch_item)

    return ExecutiveBriefing(
        briefing_date=today,
        generated_at=datetime.utcnow(),
        priorities=priorities,
        conflicts=conflicts,
        follow_ups=follow_ups,
        deadlines=deadlines,
        meetings=meetings,
        applications=applications,
    )


def briefing_needs_rebuild(briefing: dict) -> bool:
    """Cached briefings missing newer fields need regeneration."""
    for section in ("deadlines", "applications", "priorities", "follow_ups"):
        for item in briefing.get(section, []):
            if item.get("source_id") is not None and not item.get("source_table"):
                return True
    for item in briefing.get("applications", []):
        if item.get("source_id") is not None and "tracked_application" not in item:
            return True
    for item in briefing.get("priorities", []):
        if "priority_source" not in item:
            return True
    return False


def briefing_to_db_row(briefing: ExecutiveBriefing) -> dict:
    return {
        "briefing_date": briefing.briefing_date.isoformat(),
        "generated_at": briefing.generated_at.isoformat(),
        "priorities": [p.model_dump() for p in briefing.priorities],
        "conflicts": [c.model_dump() for c in briefing.conflicts],
        "follow_ups": [f.model_dump() for f in briefing.follow_ups],
        "deadlines": [d.model_dump() for d in briefing.deadlines],
        "meetings": [m.model_dump() for m in briefing.meetings],
        "applications": [a.model_dump() for a in briefing.applications],
        "summary_md": None,
    }
