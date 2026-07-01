from collections import defaultdict
from datetime import date, timedelta

from lib.assistant.collector import AssistantContext
from lib.assistant.ranker import _parse_date, item_to_briefing
from lib.schemas import BriefingItem, Conflict


def detect_conflicts(ctx: AssistantContext) -> list[Conflict]:
    today = ctx.briefing_date
    conflicts: list[Conflict] = []

    by_date: dict[str, list[BriefingItem]] = defaultdict(list)
    all_items: list[dict] = []

    for row in ctx.deadlines:
        all_items.append(
            {
                "title": row["title"],
                "category": row.get("category", "").replace("scout:", ""),
                "due_at": row.get("deadline_at"),
                "url": row.get("url"),
                "source_id": row.get("source_id"),
                "status": row.get("status"),
            }
        )

    all_items.extend(ctx.follow_ups)
    all_items.extend(ctx.launches)
    all_items.extend(ctx.meetings)

    for raw in all_items:
        due = _parse_date(raw.get("due_at"))
        if not due:
            continue
        item = item_to_briefing(raw, today)
        by_date[due.isoformat()].append(item)

    for day, items in sorted(by_date.items()):
        high_priority = [i for i in items if i.priority_score >= 30]
        if len(high_priority) >= 2:
            conflicts.append(
                Conflict(
                    summary=f"{len(high_priority)} high-priority items on {day}",
                    items=high_priority,
                    severity="high" if len(high_priority) >= 3 else "medium",
                )
            )

        categories = {i.category for i in items}
        if "travel" in categories and ("interview" in categories or "meeting" in categories):
            travel = [i for i in items if i.category == "travel"]
            scheduled = [i for i in items if i.category in ("interview", "meeting")]
            conflicts.append(
                Conflict(
                    summary=f"Travel overlaps with {len(scheduled)} scheduled event(s) on {day}",
                    items=travel + scheduled,
                    severity="high",
                )
            )

        if "launch" in categories and "travel" in categories:
            conflicts.append(
                Conflict(
                    summary=f"Launch milestone same day as travel on {day}",
                    items=[i for i in items if i.category in ("launch", "travel")],
                    severity="medium",
                )
            )

    overdue_followups = [
        item_to_briefing(f, today)
        for f in ctx.follow_ups
        if (_parse_date(f.get("due_at")) or today) < today
    ]
    urgent_apps = [
        item_to_briefing(a, today)
        for a in ctx.applications
        if (_parse_date(a.get("due_at")) or date.max) <= today + timedelta(days=3)
    ]
    if overdue_followups and urgent_apps:
        conflicts.append(
            Conflict(
                summary="Overdue follow-ups while application deadlines are approaching",
                items=(overdue_followups[:3] + urgent_apps[:3]),
                severity="high",
            )
        )

    return conflicts
