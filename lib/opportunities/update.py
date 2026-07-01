import json
from datetime import date
from typing import Any

import sqlite3

from lib.scout.profile import load_founder_profile
from lib.scout.ranker import rank_opportunity


def _parse_raw_json(value: str | dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return json.loads(value)


def update_scout_deadline(
    conn: sqlite3.Connection,
    opportunity_id: int,
    deadline_at: date | None,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM scout_opportunities WHERE id = ?",
        (opportunity_id,),
    ).fetchone()
    if not row:
        return None

    existing = dict(row)
    raw_json = _parse_raw_json(existing.get("raw_json"))

    if deadline_at is None:
        raw_json.pop("deadline_locked", None)
        raw_json.pop("deadline_source", None)
        deadline_value = None
    else:
        raw_json["deadline_locked"] = True
        raw_json["deadline_source"] = "manual"
        deadline_value = deadline_at.isoformat()

    profile = load_founder_profile()
    ranked = rank_opportunity(
        title=existing["name"],
        snippet=existing.get("description") or "",
        description=existing.get("description"),
        category=existing.get("category") or "",
        deadline_at=deadline_at,
        profile=profile,
    )

    conn.execute(
        """
        UPDATE scout_opportunities
        SET deadline_at = ?,
            score_total = ?,
            score_deadline = ?,
            rank_reason = ?,
            raw_json = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            deadline_value,
            ranked.scores.total,
            ranked.scores.deadline,
            ranked.rank_reason,
            json.dumps(raw_json) if raw_json else None,
            opportunity_id,
        ),
    )

    updated = conn.execute(
        "SELECT * FROM scout_opportunities WHERE id = ?",
        (opportunity_id,),
    ).fetchone()
    return dict(updated) if updated else None
