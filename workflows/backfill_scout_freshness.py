#!/usr/bin/env python3
"""One-time (re-runnable) cleanup for scout_opportunities rows discovered
before the freshness/extraction fixes landed.

Scoped deliberately narrow and conservative:

- Re-extracts deadline_at using the new proximity-gated parser, but only for
  agent-discovered rows (source not in manual/twitter) and never for rows
  with `deadline_locked` set — a manually-typed or manually-edited deadline
  is never touched.
- Deletes agent-discovered rows whose URL is a social-feed/post link (never
  a real application page), but only if nothing in assistant_tracks or
  application_drafts references them.
- Flags (never deletes/merges) likely-duplicate rows within the same
  category, pointing the later-discovered row at the earlier one via
  raw_json.likely_duplicate_of.

Defaults to a dry run — pass --apply to write changes. Always backs up the
database file to storage/exports/ before applying anything.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.db import get_connection, get_db_path, init_db  # noqa: E402
from lib.opportunities.intake import is_social_url  # noqa: E402
from lib.scout.profile import load_founder_profile  # noqa: E402
from lib.scout.ranker import parse_deadline_from_text, rank_opportunity  # noqa: E402
from lib.timeutil import utcnow_naive  # noqa: E402

# Only re-extract deadlines for rows whose stored text is actually a raw
# search-engine snippet — the thing the new parser is meant to fix. Deliberately
# an allowlist, not a denylist: manual/twitter saves reflect what the founder
# typed in, and other sources (e.g. "claude_verified_research" — a prior
# research pass that verified real deadlines directly against apply pages,
# storing a curated *description* rather than a scraped snippet) carry
# deadlines that didn't come from this text at all. Re-extracting from an
# unrelated summary would silently destroy good data. Any source not in this
# list is left untouched, which is the safe default for sources this script
# doesn't know about.
SNIPPET_BASED_SOURCES = frozenset({"tavily", "serpapi", "google_cse"})


def _reconstruct_text(row: dict) -> str:
    raw = json.loads(row["raw_json"]) if row.get("raw_json") else {}
    title = raw.get("title") or row.get("name") or ""
    snippet = raw.get("content") or raw.get("snippet") or row.get("description") or ""
    return f"{title} {snippet}"


def _is_deadline_locked(row: dict) -> bool:
    if not row.get("raw_json"):
        return False
    raw = json.loads(row["raw_json"])
    return bool(raw.get("deadline_locked"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()

    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM scout_opportunities").fetchall()]

    # --- referenced ids (never delete these, no matter what) ---
    with get_connection() as conn:
        tracked = {
            int(r["source_id"])
            for r in conn.execute(
                "SELECT source_id FROM assistant_tracks WHERE source_table = 'scout_opportunities'"
            ).fetchall()
        }
        drafted = {
            int(r["source_id"])
            for r in conn.execute(
                "SELECT source_id FROM application_drafts WHERE source_table = 'scout_opportunities'"
            ).fetchall()
        }
    protected_ids = tracked | drafted

    # --- 1. social-host deletions ---
    to_delete: list[dict] = []
    for row in rows:
        if row["source"] not in SNIPPET_BASED_SOURCES:
            continue
        if row["id"] in protected_ids:
            continue
        if row["url"] and is_social_url(row["url"]):
            to_delete.append(row)

    delete_ids = {r["id"] for r in to_delete}
    remaining = [r for r in rows if r["id"] not in delete_ids]

    # --- 2. deadline re-extraction (snippet-sourced, not locked) ---
    profile = load_founder_profile()
    deadline_updates: list[dict] = []
    for row in remaining:
        if row["source"] not in SNIPPET_BASED_SOURCES:
            continue
        if _is_deadline_locked(row):
            continue
        text = _reconstruct_text(row)
        new_deadline = parse_deadline_from_text(text)
        new_deadline_str = new_deadline.isoformat() if new_deadline else None
        if new_deadline_str == row.get("deadline_at"):
            continue
        ranked = rank_opportunity(
            title=row.get("name") or "",
            snippet=row.get("description") or "",
            description=row.get("description"),
            category=row.get("category") or "",
            deadline_at=new_deadline,
            profile=profile,
        )
        deadline_updates.append(
            {
                "id": row["id"],
                "name": row["name"],
                "old_deadline": row.get("deadline_at"),
                "new_deadline": new_deadline_str,
                "old_score": row.get("score_total"),
                "new_score": ranked.scores.total,
                "new_score_deadline": ranked.scores.deadline,
                "new_rank_reason": ranked.rank_reason,
            }
        )

    # --- 3. duplicate flagging (later id -> earlier id, same category) ---
    by_category: dict[str, list[dict]] = {}
    for row in remaining:
        by_category.setdefault(row["category"], []).append(row)

    import difflib
    import re

    def _normalize(text: str) -> str:
        text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        return re.sub(r"\s+", " ", text).strip()

    duplicate_tags: list[dict] = []
    for _category, items in by_category.items():
        items_sorted = sorted(items, key=lambda r: r["id"])
        for i, row in enumerate(items_sorted):
            if _is_deadline_locked(row):
                continue  # don't relabel a manually-curated row as a duplicate
            already_tagged = False
            if row.get("raw_json"):
                already_tagged = bool(json.loads(row["raw_json"]).get("likely_duplicate_of"))
            if already_tagged:
                continue
            name_norm = _normalize(row["name"])
            if not name_norm:
                continue
            best_id = None
            best_ratio = 0.0
            for earlier in items_sorted[:i]:
                earlier_norm = _normalize(earlier["name"])
                if not earlier_norm:
                    continue
                ratio = difflib.SequenceMatcher(None, name_norm, earlier_norm).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_id = earlier["id"]
            if best_id is not None and best_ratio >= 0.85:
                duplicate_tags.append({"id": row["id"], "name": row["name"], "duplicate_of": best_id, "ratio": round(best_ratio, 3)})

    # --- report ---
    print(f"Database: {db_path}")
    print(f"Total scout_opportunities rows: {len(rows)}")
    print()
    print(f"1. Social-host rows to delete ({len(to_delete)}):")
    for r in to_delete:
        print(f"   #{r['id']:>4}  {r['name'][:60]!r}  {r['url']}")
    print()
    print(f"2. Deadline re-extractions ({len(deadline_updates)}):")
    for u in deadline_updates:
        print(
            f"   #{u['id']:>4}  {u['name'][:45]!r}  "
            f"deadline: {u['old_deadline']!r} -> {u['new_deadline']!r}  "
            f"score: {u['old_score']} -> {u['new_score']}"
        )
    print()
    print(f"3. Likely-duplicate flags ({len(duplicate_tags)}):")
    for d in duplicate_tags:
        print(f"   #{d['id']:>4} {d['name'][:40]!r}  ~duplicate of #{d['duplicate_of']}  (similarity {d['ratio']})")
    print()

    if not args.apply:
        print("Dry run only — no changes written. Re-run with --apply to commit these changes.")
        return

    backup_dir = ROOT / "storage" / "exports"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"founder_os_pre_backfill_{utcnow_naive().strftime('%Y%m%dT%H%M%SZ')}.db"
    shutil.copy2(db_path, backup_path)
    print(f"Backed up database to {backup_path}")

    with get_connection() as conn:
        for r in to_delete:
            conn.execute("DELETE FROM scout_opportunities WHERE id = ?", (r["id"],))

        for u in deadline_updates:
            conn.execute(
                """
                UPDATE scout_opportunities
                SET deadline_at = ?, score_total = ?, score_deadline = ?, rank_reason = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (u["new_deadline"], u["new_score"], u["new_score_deadline"], u["new_rank_reason"], u["id"]),
            )

        for d in duplicate_tags:
            row = conn.execute(
                "SELECT raw_json FROM scout_opportunities WHERE id = ?", (d["id"],)
            ).fetchone()
            if row is None:
                continue
            raw = json.loads(row["raw_json"]) if row["raw_json"] else {}
            raw["likely_duplicate_of"] = d["duplicate_of"]
            conn.execute(
                "UPDATE scout_opportunities SET raw_json = ? WHERE id = ?",
                (json.dumps(raw), d["id"]),
            )

    print(
        f"Applied: deleted {len(to_delete)}, re-extracted {len(deadline_updates)} deadlines, "
        f"flagged {len(duplicate_tags)} likely duplicates."
    )


if __name__ == "__main__":
    main()
