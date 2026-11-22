#!/usr/bin/env python3
"""Re-score every stored scout opportunity with the current ranker.

Scores are written when an opportunity is first found, so ranker changes only
reach rows a later scan rediscovers. Run this after changing the ranker:

    python workflows/rescore_scout.py           # dry run: show what moves
    python workflows/rescore_scout.py --apply   # back up the DB, then write

Deadlines, tracking, drafts and all non-score columns are left untouched.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from lib.db import get_connection, get_db_path, init_db  # noqa: E402
from lib.scout.profile import load_founder_profile  # noqa: E402
from lib.scout.ranker import rank_opportunity  # noqa: E402
from lib.timeutil import utcnow_naive  # noqa: E402

SCORE_COLUMNS = {
    "score_total": "total",
    "score_stage_fit": "stage_fit",
    "score_ai_focus": "ai_focus",
    "score_education": "education_focus",
    "score_language_preservation": "language_preservation",
    "score_minority_founder": "minority_founder",
    "score_deadline": "deadline",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Write new scores (default: dry run)")
    args = parser.parse_args()

    init_db()
    profile = load_founder_profile()
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM scout_opportunities").fetchall()]
        updates = []
        for row in rows:
            deadline = date.fromisoformat(row["deadline_at"][:10]) if row.get("deadline_at") else None
            ranked = rank_opportunity(
                title=row["name"],
                snippet=row.get("description") or "",
                category=row.get("category") or "",
                deadline_at=deadline,
                profile=profile,
            )
            scores = ranked.scores.model_dump()
            new = {col: scores[field] for col, field in SCORE_COLUMNS.items()}
            updates.append((row, new, ranked.rank_reason))

        old_top = [r["name"] for r in sorted(rows, key=lambda r: -(r["score_total"] or 0))[:10]]
        new_top = [r["name"] for r, n, _ in sorted(updates, key=lambda u: -u[1]["score_total"])[:10]]
        changed = sum(1 for r, n, _ in updates if abs((r["score_total"] or 0) - n["score_total"]) >= 0.05)
        print(f"{len(rows)} opportunities, {changed} with a changed total score")
        print(f"top-10 overlap before/after: {len(set(old_top) & set(new_top))}/10\n")
        print("New top 10:")
        for i, name in enumerate(new_top, 1):
            print(f"  {i:2}. {name[:90]}{'' if name in old_top else '   (new)'}")

        if not args.apply:
            print("\nDry run — pass --apply to write.")
            return

        db_path = get_db_path()
        backup = ROOT / "storage" / "exports" / f"founder_os_pre_rescore_{utcnow_naive():%Y%m%dT%H%M%SZ}.db"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, backup)
        assignments = ", ".join(f"{col} = ?" for col in SCORE_COLUMNS)
        conn.executemany(
            f"UPDATE scout_opportunities SET {assignments}, rank_reason = ?, updated_at = datetime('now') WHERE id = ?",
            [(*new.values(), reason, row["id"]) for row, new, reason in updates],
        )
        print(f"\nUpdated {len(updates)} rows. Backup: {backup.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
