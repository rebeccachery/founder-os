import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Generator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "storage" / "founder_os.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS investors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    firm TEXT,
    stage TEXT,
    thesis TEXT,
    url TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS funding_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    organization TEXT,
    amount TEXT,
    stage TEXT,
    description TEXT,
    url TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    funder TEXT,
    amount TEXT,
    eligibility TEXT,
    url TEXT UNIQUE,
    deadline_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    organizer TEXT,
    prize TEXT,
    url TEXT UNIQUE,
    deadline_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scout_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    organization TEXT,
    amount TEXT,
    stage TEXT,
    description TEXT,
    url TEXT UNIQUE,
    deadline_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    score_total REAL,
    score_stage_fit REAL,
    score_ai_focus REAL,
    score_education REAL,
    score_language_preservation REAL,
    score_minority_founder REAL,
    score_deadline REAL,
    rank_reason TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    organization TEXT,
    email TEXT,
    role TEXT,
    notes TEXT,
    last_touch_at TEXT,
    next_follow_up_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    items_found INTEGER NOT NULL DEFAULT 0,
    items_upserted INTEGER NOT NULL DEFAULT 0,
    message TEXT
);

CREATE TABLE IF NOT EXISTS oss_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    description TEXT,
    organization TEXT,
    license TEXT,
    stars INTEGER,
    task_tags TEXT,
    language_tags TEXT,
    metrics_json TEXT,
    published_at TEXT,
    last_updated_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    score_total REAL,
    score_task_fit REAL,
    score_language_fit REAL,
    score_recency REAL,
    score_popularity REAL,
    rank_reason TEXT,
    raw_json TEXT,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scout_score ON scout_opportunities(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_scout_deadline ON scout_opportunities(deadline_at);
CREATE INDEX IF NOT EXISTS idx_scout_category ON scout_opportunities(category);
CREATE INDEX IF NOT EXISTS idx_grants_deadline ON grants(deadline_at);
CREATE INDEX IF NOT EXISTS idx_competitions_deadline ON competitions(deadline_at);
CREATE INDEX IF NOT EXISTS idx_investors_status ON investors(status);
CREATE INDEX IF NOT EXISTS idx_contacts_follow_up ON contacts(next_follow_up_at);
CREATE INDEX IF NOT EXISTS idx_oss_score ON oss_resources(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_oss_type ON oss_resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_oss_status ON oss_resources(status);

CREATE TABLE IF NOT EXISTS social_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,
    platform TEXT,
    title TEXT,
    body TEXT NOT NULL,
    hook TEXT,
    source_refs TEXT,
    signal_score REAL,
    status TEXT NOT NULL DEFAULT 'draft',
    llm_model TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    posted_at TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_social_status ON social_posts(status);
CREATE INDEX IF NOT EXISTS idx_social_type ON social_posts(content_type);
CREATE INDEX IF NOT EXISTS idx_social_generated ON social_posts(generated_at DESC);

CREATE TABLE IF NOT EXISTS executive_briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    briefing_date TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL,
    priorities_json TEXT NOT NULL,
    conflicts_json TEXT NOT NULL,
    follow_ups_json TEXT NOT NULL,
    deadlines_json TEXT NOT NULL,
    meetings_json TEXT NOT NULL,
    applications_json TEXT NOT NULL,
    summary_md TEXT
);

CREATE INDEX IF NOT EXISTS idx_briefing_date ON executive_briefings(briefing_date DESC);
"""


def get_db_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))


def purge_test_rows(conn: sqlite3.Connection) -> None:
    """Remove placeholder rows used during local development."""
    for table in ("scout_opportunities", "oss_resources"):
        conn.execute(
            f"DELETE FROM {table} WHERE url LIKE '%example.com%'"
        )


def init_db(db_path: Path | None = None) -> None:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        purge_test_rows(conn)
        conn.commit()


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or get_db_path()
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _serialize_json(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _parse_json(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    return json.loads(value)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def upsert_by_url(
    conn: sqlite3.Connection,
    table: str,
    data: dict[str, Any],
    url_key: str = "url",
) -> int:
    url = data.get(url_key)
    if not url:
        raise ValueError(f"{table} row requires {url_key}")

    raw_json = data.get("raw_json")
    if isinstance(raw_json, dict):
        data = {**data, "raw_json": _serialize_json(raw_json)}

    columns = [k for k in data.keys() if k != "id"]
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in ("created_at",))
    updates += ", updated_at=datetime('now')"

    sql = f"""
        INSERT INTO {table} ({col_names})
        VALUES ({placeholders})
        ON CONFLICT({url_key}) DO UPDATE SET {updates}
    """
    conn.execute(sql, [data[c] for c in columns])
    row = conn.execute(f"SELECT id FROM {table} WHERE {url_key} = ?", (url,)).fetchone()
    return int(row["id"])


def list_table(
    conn: sqlite3.Connection,
    table: str,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if status:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_deadlines(conn: sqlite3.Connection, days: int = 30) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    deadlines: list[dict[str, Any]] = []

    grant_rows = conn.execute(
        """
        SELECT id, name AS title, deadline_at, url, status
        FROM grants
        WHERE deadline_at IS NOT NULL
          AND deadline_at >= ?
          AND deadline_at <= ?
        ORDER BY deadline_at ASC
        """,
        (today, cutoff),
    ).fetchall()
    for row in grant_rows:
        deadlines.append(
            {
                "id": row["id"],
                "title": row["title"],
                "deadline_at": row["deadline_at"],
                "category": "grant",
                "source_id": row["id"],
                "url": row["url"],
                "is_estimated": False,
                "status": row["status"],
            }
        )

    comp_rows = conn.execute(
        """
        SELECT id, name AS title, deadline_at, url, status
        FROM competitions
        WHERE deadline_at IS NOT NULL
          AND deadline_at >= ?
          AND deadline_at <= ?
        ORDER BY deadline_at ASC
        """,
        (today, cutoff),
    ).fetchall()
    for row in comp_rows:
        deadlines.append(
            {
                "id": row["id"],
                "title": row["title"],
                "deadline_at": row["deadline_at"],
                "category": "competition",
                "source_id": row["id"],
                "url": row["url"],
                "is_estimated": False,
                "status": row["status"],
            }
        )

    scout_rows = conn.execute(
        """
        SELECT id, name AS title, deadline_at, url, status, category, source
        FROM scout_opportunities
        WHERE deadline_at IS NOT NULL
          AND deadline_at >= ?
          AND deadline_at <= ?
        ORDER BY deadline_at ASC
        """,
        (today, cutoff),
    ).fetchall()
    for row in scout_rows:
        deadlines.append(
            {
                "id": row["id"],
                "title": row["title"],
                "deadline_at": row["deadline_at"],
                "category": f"scout:{row['category']}",
                "source_id": row["id"],
                "url": row["url"],
                "is_estimated": False,
                "status": row["status"],
                "source": row["source"],
            }
        )

    contact_rows = conn.execute(
        """
        SELECT id, name AS title, next_follow_up_at AS deadline_at, NULL AS url, status
        FROM contacts
        WHERE next_follow_up_at IS NOT NULL
          AND next_follow_up_at >= ?
          AND next_follow_up_at <= ?
        ORDER BY next_follow_up_at ASC
        """,
        (today, cutoff),
    ).fetchall()
    for row in contact_rows:
        deadlines.append(
            {
                "id": row["id"],
                "title": f"Follow up: {row['title']}",
                "deadline_at": row["deadline_at"],
                "category": "crm",
                "source_id": row["id"],
                "url": row["url"],
                "is_estimated": False,
                "status": row["status"],
            }
        )

    deadlines.sort(key=lambda d: d["deadline_at"] or "")
    return deadlines


def get_stats(conn: sqlite3.Connection) -> dict[str, int]:
    def count(table: str) -> int:
        row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
        return int(row["c"])

    upcoming = len(get_deadlines(conn, days=30))

    new_items = 0
    for table in (
        "investors",
        "funding_opportunities",
        "grants",
        "competitions",
        "scout_opportunities",
        "oss_resources",
    ):
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM {table} WHERE status = 'new'"
        ).fetchone()
        new_items += int(row["c"])

    draft_row = conn.execute(
        "SELECT COUNT(*) AS c FROM social_posts WHERE status = 'draft'"
    ).fetchone()
    social_drafts = int(draft_row["c"])

    return {
        "investors": count("investors"),
        "funding": count("funding_opportunities"),
        "grants": count("grants"),
        "competitions": count("competitions"),
        "scout": count("scout_opportunities"),
        "oss": count("oss_resources"),
        "social": social_drafts,
        "deadlines_upcoming": upcoming,
        "contacts": count("contacts"),
        "new_items": new_items,
    }


def list_scout_opportunities(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    category: str | None = None,
    source: str | None = None,
    min_score: float | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if source:
        if source == "manual":
            clauses.append("source IN ('manual', 'twitter')")
        elif source == "agent":
            clauses.append("(source IS NULL OR source NOT IN ('manual', 'twitter'))")
        else:
            clauses.append("source = ?")
            params.append(source)
    if min_score is not None:
        clauses.append("score_total >= ?")
        params.append(min_score)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM scout_opportunities
        {where}
        ORDER BY COALESCE(score_total, -1) DESC, updated_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _oss_recent_clause(recent_days: int) -> tuple[str, str]:
    """Match items updated or first discovered within the recent window."""
    clause = (
        "COALESCE(last_updated_at, discovered_at) IS NOT NULL AND "
        "datetime(COALESCE(last_updated_at, discovered_at)) >= datetime('now', ?)"
    )
    return clause, f"-{recent_days} days"


def list_oss_resources(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    resource_type: str | None = None,
    min_score: float | None = None,
    view: str = "all",
    recent_days: int = 90,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if resource_type:
        clauses.append("resource_type = ?")
        params.append(resource_type)
    if min_score is not None:
        clauses.append("score_total >= ?")
        params.append(min_score)

    if view == "recent":
        recent_clause, recent_param = _oss_recent_clause(recent_days)
        clauses.append(recent_clause)
        params.append(recent_param)
    elif view == "reference":
        recent_clause, recent_param = _oss_recent_clause(recent_days)
        clauses.append("resource_type IN ('benchmark', 'eval_tool')")
        clauses.append(
            f"(COALESCE(last_updated_at, discovered_at) IS NULL OR NOT ({recent_clause}))"
        )
        params.append(recent_param)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM oss_resources
        {where}
        ORDER BY COALESCE(score_total, -1) DESC, updated_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def archive_draft_social_posts_for_date(conn: sqlite3.Connection, day: str) -> int:
    cursor = conn.execute(
        """
        UPDATE social_posts
        SET status = 'archived', updated_at = datetime('now')
        WHERE status = 'draft' AND date(generated_at) = date(?)
        """,
        (day,),
    )
    return cursor.rowcount


def insert_social_post(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    source_refs = data.get("source_refs")
    if isinstance(source_refs, list):
        data = {**data, "source_refs": json.dumps(source_refs)}
    raw_json = data.get("raw_json")
    if isinstance(raw_json, dict):
        data = {**data, "raw_json": _serialize_json(raw_json)}

    columns = [k for k in data.keys() if k != "id"]
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    conn.execute(
        f"INSERT INTO social_posts ({col_names}) VALUES ({placeholders})",
        [data[c] for c in columns],
    )
    row = conn.execute("SELECT last_insert_rowid() AS id").fetchone()
    return int(row["id"])


def list_social_posts(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    content_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if content_type:
        clauses.append("content_type = ?")
        params.append(content_type)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM social_posts
        {where}
        ORDER BY generated_at DESC, id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_social_post(conn: sqlite3.Connection, post_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def update_social_post_status(
    conn: sqlite3.Connection,
    post_id: int,
    status: str,
    *,
    body: str | None = None,
    posted_at: str | None = None,
) -> bool:
    fields = ["status = ?", "updated_at = datetime('now')"]
    params: list[Any] = [status]

    if body is not None:
        fields.append("body = ?")
        params.append(body)
    if posted_at is not None:
        fields.append("posted_at = ?")
        params.append(posted_at)
    elif status == "posted":
        fields.append("posted_at = datetime('now')")

    params.append(post_id)
    cursor = conn.execute(
        f"UPDATE social_posts SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    return cursor.rowcount > 0


def get_last_agent_run(
    conn: sqlite3.Connection,
    agent_name: str,
    *,
    status: str = "success",
) -> datetime | None:
    row = conn.execute(
        """
        SELECT started_at FROM agent_runs
        WHERE agent_name = ? AND status = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (agent_name, status),
    ).fetchone()
    if not row or not row["started_at"]:
        return None
    return datetime.fromisoformat(row["started_at"])


def log_agent_run(
    conn: sqlite3.Connection,
    agent_name: str,
    started_at: datetime,
    status: str,
    items_found: int = 0,
    items_upserted: int = 0,
    message: str | None = None,
    finished_at: datetime | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO agent_runs (agent_name, started_at, finished_at, status, items_found, items_upserted, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_name,
            started_at.isoformat(),
            (finished_at or datetime.utcnow()).isoformat(),
            status,
            items_found,
            items_upserted,
            message,
        ),
    )


def _briefing_section_to_json(items: list[Any]) -> str:
    return json.dumps(items)


def _briefing_section_from_json(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    return json.loads(raw)


def upsert_briefing(conn: sqlite3.Connection, briefing: dict[str, Any]) -> int:
    conn.execute(
        """
        INSERT INTO executive_briefings (
            briefing_date, generated_at,
            priorities_json, conflicts_json, follow_ups_json,
            deadlines_json, meetings_json, applications_json, summary_md
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(briefing_date) DO UPDATE SET
            generated_at = excluded.generated_at,
            priorities_json = excluded.priorities_json,
            conflicts_json = excluded.conflicts_json,
            follow_ups_json = excluded.follow_ups_json,
            deadlines_json = excluded.deadlines_json,
            meetings_json = excluded.meetings_json,
            applications_json = excluded.applications_json,
            summary_md = excluded.summary_md
        """,
        (
            briefing["briefing_date"],
            briefing["generated_at"],
            _briefing_section_to_json(briefing["priorities"]),
            _briefing_section_to_json(briefing["conflicts"]),
            _briefing_section_to_json(briefing["follow_ups"]),
            _briefing_section_to_json(briefing["deadlines"]),
            _briefing_section_to_json(briefing["meetings"]),
            _briefing_section_to_json(briefing["applications"]),
            briefing.get("summary_md"),
        ),
    )
    row = conn.execute(
        "SELECT id FROM executive_briefings WHERE briefing_date = ?",
        (briefing["briefing_date"],),
    ).fetchone()
    return int(row["id"])


def get_briefing(conn: sqlite3.Connection, briefing_date: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM executive_briefings WHERE briefing_date = ?",
        (briefing_date,),
    ).fetchone()
    if not row:
        return None
    return _briefing_row_to_dict(row)


def get_latest_briefing(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM executive_briefings
        ORDER BY briefing_date DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return _briefing_row_to_dict(row)


def _briefing_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "briefing_date": row["briefing_date"],
        "generated_at": row["generated_at"],
        "priorities": _briefing_section_from_json(row["priorities_json"]),
        "conflicts": _briefing_section_from_json(row["conflicts_json"]),
        "follow_ups": _briefing_section_from_json(row["follow_ups_json"]),
        "deadlines": _briefing_section_from_json(row["deadlines_json"]),
        "meetings": _briefing_section_from_json(row["meetings_json"]),
        "applications": _briefing_section_from_json(row["applications_json"]),
        "summary_md": row["summary_md"],
    }


def seed_demo_data(conn: sqlite3.Connection) -> None:
    """Insert sample rows so the dashboard is usable before agents run."""
    existing = conn.execute("SELECT COUNT(*) AS c FROM investors").fetchone()
    if int(existing["c"]) > 0:
        return

    demo_investors = [
        {
            "name": "Example Seed Fund",
            "firm": "Example Capital",
            "stage": "pre-seed",
            "thesis": "B2B SaaS, developer tools",
            "url": "https://example.com/investors/seed-fund",
            "status": "new",
            "source": "seed",
        },
        {
            "name": "North Star Ventures",
            "firm": "North Star",
            "stage": "seed",
            "thesis": "Climate, deep tech",
            "url": "https://example.com/investors/north-star",
            "status": "reviewed",
            "source": "seed",
        },
    ]
    for inv in demo_investors:
        upsert_by_url(conn, "investors", inv)

    demo_grants = [
        {
            "name": "Small Business Innovation Grant",
            "funder": "Example Foundation",
            "amount": "$50,000",
            "eligibility": "Early-stage startups, US-based",
            "url": "https://example.com/grants/sbig",
            "deadline_at": (date.today() + timedelta(days=14)).isoformat(),
            "status": "new",
            "source": "seed",
        },
    ]
    for grant in demo_grants:
        upsert_by_url(conn, "grants", grant)

    demo_comps = [
        {
            "name": "Startup Pitch Championship",
            "organizer": "TechWeek",
            "prize": "$25,000",
            "url": "https://example.com/competitions/pitch",
            "deadline_at": (date.today() + timedelta(days=21)).isoformat(),
            "status": "new",
            "source": "seed",
        },
    ]
    for comp in demo_comps:
        upsert_by_url(conn, "competitions", comp)

    demo_funding = [
        {
            "name": "Accelerator Batch Q3",
            "organization": "LaunchPad",
            "amount": "$150,000",
            "stage": "pre-seed",
            "description": "12-week program with demo day",
            "url": "https://example.com/funding/launchpad",
            "status": "new",
            "source": "seed",
        },
    ]
    for opp in demo_funding:
        upsert_by_url(conn, "funding_opportunities", opp)
