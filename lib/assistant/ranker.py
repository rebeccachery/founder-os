from datetime import date, timedelta

from lib.assistant.collector import AssistantContext
from lib.schemas import BriefingItem


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _days_until(due: date | None, today: date) -> int | None:
    if due is None:
        return None
    return (due - today).days


def _deadline_urgency_score(days_out: int | None) -> float:
    if days_out is None:
        return 5.0
    if days_out < 0:
        return 45.0
    if days_out == 0:
        return 50.0
    if days_out <= 3:
        return 30.0
    if days_out <= 7:
        return 20.0
    if days_out <= 14:
        return 10.0
    return 0.0


def _reason_for_item(item: dict, today: date) -> str:
    due = _parse_date(item.get("due_at"))
    days = _days_until(due, today)
    category = item.get("category", "")

    if item.get("pin_priority"):
        return "Pinned priority"
    if days is not None and days < 0:
        return f"Overdue by {abs(days)} day{'s' if abs(days) != 1 else ''}"
    if days == 0:
        return "Due today"
    if days is not None and days <= 3:
        return f"Due in {days} day{'s' if days != 1 else ''}"
    if item.get("status") == "new":
        return "Unreviewed application"
    if category == "crm":
        return "Scheduled follow-up"
    if category == "launch":
        return "Upcoming launch milestone"
    if item.get("score_total") and item["score_total"] >= 60:
        return "High scout score"
    if item.get("source") == "twitter":
        return "Saved from Twitter"
    if item.get("source") == "manual":
        return "Saved by you"
    return "Upcoming deadline"


def score_item(item: dict, today: date) -> float:
    score = 0.0
    due = _parse_date(item.get("due_at"))
    days = _days_until(due, today)

    score += _deadline_urgency_score(days)

    scout_score = item.get("score_total")
    if scout_score is not None:
        score += min(30.0, scout_score * 0.3)

    if item.get("status") == "new":
        score += 15.0

    if item.get("category") == "crm" and days is not None and days < 0:
        score += 40.0

    if item.get("category") == "launch" and days is not None and 0 <= days <= 7:
        score += 25.0

    if item.get("source") in ("manual", "twitter"):
        score += 10.0

    if item.get("pin_priority"):
        score += 100.0

    return round(score, 1)


def item_to_briefing(item: dict, today: date) -> BriefingItem:
    return BriefingItem(
        title=item["title"],
        category=item.get("category", "other"),
        due_at=item.get("due_at"),
        priority_score=score_item(item, today),
        reason=_reason_for_item(item, today),
        url=item.get("url"),
        source_id=item.get("source_id"),
        source_table=item.get("source_table"),
        status=item.get("status"),
        pin_priority=bool(item.get("pin_priority")),
        tracked_application=bool(item.get("tracked_application")),
        priority_source=item.get("priority_source", "auto"),
    )


def _is_dismissed(track: dict | None, today: date) -> bool:
    if not track or not track.get("dismissed_until"):
        return False
    dismissed_until = _parse_date(track["dismissed_until"])
    return dismissed_until is not None and dismissed_until >= today


def _merge_track_fields(item: dict, track: dict | None) -> dict:
    merged = dict(item)
    if track:
        merged["pin_priority"] = track.get("pin_priority", False)
        merged["tracked_application"] = track.get("track_application", False)
        merged["dismissed"] = _is_dismissed(track, date.today())
    else:
        merged.setdefault("pin_priority", False)
        merged.setdefault("tracked_application", False)
        merged.setdefault("dismissed", False)
    return merged


def rank_priorities(
    ctx: AssistantContext,
    tracks: dict[int, dict],
    *,
    limit: int = 7,
) -> list[BriefingItem]:
    today = ctx.briefing_date
    pinned_raw: list[dict] = []
    candidates: list[dict] = []

    for row in ctx.deadlines:
        raw = {
            "title": row["title"],
            "category": row["category"].replace("scout:", "") if row.get("category") else "deadline",
            "due_at": row.get("deadline_at"),
            "url": row.get("url"),
            "source_id": row.get("source_id"),
            "source_table": row.get("source_table"),
            "status": row.get("status"),
            "source": row.get("source"),
        }
        sid = raw.get("source_id")
        track = tracks.get(int(sid)) if sid is not None else None
        raw = _merge_track_fields(raw, track)
        if raw.get("pin_priority") and raw.get("source_table") == "scout_opportunities":
            raw["priority_source"] = "pinned"
            pinned_raw.append(raw)
        candidates.append(raw)

    for follow_up in ctx.follow_ups:
        candidates.append(_merge_track_fields(follow_up, None))

    for launch in ctx.launches:
        candidates.append(_merge_track_fields(launch, None))

    for app in ctx.applications:
        sid = app.get("source_id")
        track = tracks.get(int(sid)) if sid is not None else None
        raw = _merge_track_fields(app, track)
        due = _parse_date(raw.get("due_at"))
        if due is not None and due < today - timedelta(days=7):
            continue
        if raw.get("pin_priority"):
            raw["priority_source"] = "pinned"
            key = (raw["title"], raw.get("due_at"), raw.get("source_id"))
            if not any(
                (p["title"], p.get("due_at"), p.get("source_id")) == key for p in pinned_raw
            ):
                pinned_raw.append(raw)
            continue
        if _is_dismissed(track, today):
            continue
        if due is None or due <= today + timedelta(days=14):
            candidates.append(raw)

    seen: set[tuple[str, str | None, int | None]] = set()
    pinned_items: list[BriefingItem] = []
    for raw in sorted(pinned_raw, key=lambda r: r.get("due_at") or "9999"):
        key = (raw["title"], raw.get("due_at"), raw.get("source_id"))
        if key in seen:
            continue
        seen.add(key)
        pinned_items.append(item_to_briefing(raw, today))

    auto_items: list[BriefingItem] = []
    for raw in candidates:
        key = (raw["title"], raw.get("due_at"), raw.get("source_id"))
        if key in seen:
            continue
        seen.add(key)
        briefing = item_to_briefing({**raw, "priority_source": "auto"}, today)
        if briefing.priority_score >= 10 or _parse_date(raw.get("due_at")) == today:
            auto_items.append(briefing)

    auto_items.sort(key=lambda i: (-i.priority_score, i.due_at or "9999"))

    if len(pinned_items) >= limit:
        return pinned_items

    slots = limit - len(pinned_items)
    return pinned_items + auto_items[:slots]
