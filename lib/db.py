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
"""


def get_db_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))


def init_db(db_path: Path | None = None) -> None:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
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
        SELECT id, name AS title, deadline_at, url, status, category
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

    return {
        "investors": count("investors"),
        "funding": count("funding_opportunities"),
        "grants": count("grants"),
        "competitions": count("competitions"),
        "scout": count("scout_opportunities"),
        "oss": count("oss_resources"),
        "deadlines_upcoming": upcoming,
        "contacts": count("contacts"),
        "new_items": new_items,
    }


def list_scout_opportunities(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    category: str | None = None,
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
