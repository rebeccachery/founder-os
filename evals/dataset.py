"""Evaluation data: labeled candidates for the funding scout ranker.

Three sources, in decreasing order of trustworthiness:

* **gold** — hand labels from ``python -m evals.label`` (``private/evals/scout_labels.jsonl``,
  gitignored because it reflects one founder's judgment of real listings).
* **silver** — derived from the live database: opportunities a human or a
  verification pass curated (``source`` in ``CURATED_SOURCES``) are positives;
  raw search hits are treated as negatives. Raw hits include some genuinely good
  listings, so silver metrics understate every system — useful for comparing
  systems against each other, not as absolute numbers.
* **fixture** — a small synthetic set committed to the repo so CI can run the
  harness end to end without private data.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from lib.paths import ROOT, private_dir

FIXTURE_PATH = ROOT / "evals" / "fixtures" / "synthetic_scout.jsonl"
CURATED_SOURCES = ("manual", "claude_verified_research")


def gold_labels_path() -> Path:
    return private_dir() / "evals" / "scout_labels.jsonl"


@dataclass
class Candidate:
    id: str
    title: str
    snippet: str
    category: str
    deadline_at: date | None
    label: int  # 0 = not relevant, 1 = worth a look, 2 = would apply
    source: str = ""

    @property
    def text(self) -> str:
        return f"{self.title} {self.snippet}"

    def to_json(self) -> str:
        data = asdict(self)
        data["deadline_at"] = self.deadline_at.isoformat() if self.deadline_at else None
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> Candidate:
        deadline = data.get("deadline_at")
        return cls(
            id=str(data["id"]),
            title=data["title"],
            snippet=data.get("snippet") or "",
            category=data.get("category") or "other",
            deadline_at=date.fromisoformat(deadline[:10]) if deadline else None,
            label=int(data["label"]),
            source=data.get("source") or "",
        )


def load_jsonl(path: Path) -> list[Candidate]:
    with path.open() as f:
        return [Candidate.from_dict(json.loads(line)) for line in f if line.strip()]


def _rows(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT id, name, description, category, deadline_at, source, score_total "
            "FROM scout_opportunities ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def _candidate(row: sqlite3.Row, label: int) -> Candidate:
    return Candidate.from_dict(
        {
            "id": row["id"],
            "title": row["name"],
            "snippet": row["description"],
            "category": row["category"],
            "deadline_at": row["deadline_at"],
            "label": label,
            "source": row["source"],
        }
    )


def load_silver(db_path: Path) -> list[Candidate]:
    return [_candidate(row, 2 if row["source"] in CURATED_SOURCES else 0) for row in _rows(db_path)]


def unlabeled_from_db(db_path: Path) -> list[tuple[Candidate, float]]:
    """All raw search hits (curated rows excluded, they're labeled by construction) with stored scores."""
    return [
        (_candidate(row, -1), float(row["score_total"] or 0))
        for row in _rows(db_path)
        if row["source"] not in CURATED_SOURCES
    ]
