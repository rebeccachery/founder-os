import json
from datetime import date
from typing import Any

import sqlite3

from lib.scout.profile import load_founder_profile
from lib.scout.ranker import rank_opportunity

DEADLINE_EDITABLE_TABLES = frozenset({"scout_opportunities", "grants", "competitions"})


def _parse_raw_json(value: str | dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return json.loads(value)


def _apply_manual_deadline(raw_json: dict[str, Any], deadline_at: date | None) -> tuple[str | None, dict[str, Any]]:
    if deadline_at is None:
        raw_json.pop("deadline_locked", None)
        raw_json.pop("deadline_source", None)
        return None, raw_json

    raw_json["deadline_locked"] = True
    raw_json["deadline_source"] = "manual"
    return deadline_at.isoformat(), raw_json


def update_record_deadline(
    conn: sqlite3.Connection,
    table: str,
    record_id: int,
    deadline_at: date | None,
) -> dict[str, Any] | None:
    if table not in DEADLINE_EDITABLE_TABLES:
        raise ValueError(f"Unsupported table: {table}")

    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
    if not row:
        return None

    existing = dict(row)
    raw_json = _parse_raw_json(existing.get("raw_json"))
    deadline_value, raw_json = _apply_manual_deadline(raw_json, deadline_at)
    raw_json_str = json.dumps(raw_json) if raw_json else None

    if table == "scout_opportunities":
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
                raw_json_str,
                record_id,
            ),
        )
    else:
        conn.execute(
            f"""
            UPDATE {table}
            SET deadline_at = ?,
                raw_json = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (deadline_value, raw_json_str, record_id),
        )

    updated = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
    return dict(updated) if updated else None


def update_scout_deadline(
    conn: sqlite3.Connection,
    opportunity_id: int,
    deadline_at: date | None,
) -> dict[str, Any] | None:
    return update_record_deadline(conn, "scout_opportunities", opportunity_id, deadline_at)
