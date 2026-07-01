from datetime import datetime, timezone

import sqlite3

from lib.db import archive_draft_social_posts_for_date, insert_social_post
from lib.schemas import SocialDraft, SocialGenerationResult


def save_generation_drafts(
    conn: sqlite3.Connection,
    generation: SocialGenerationResult,
) -> int:
    """Persist drafts to social_posts; archive prior drafts from the same UTC day."""
    today = datetime.now(timezone.utc).date().isoformat()
    archive_draft_social_posts_for_date(conn, today)

    saved = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    for draft in generation.drafts:
        _insert_draft(conn, draft, generation.llm_model, generated_at=now)
        saved += 1
    return saved


def _insert_draft(
    conn: sqlite3.Connection,
    draft: SocialDraft,
    llm_model: str | None,
    *,
    generated_at: str,
) -> int:
    return insert_social_post(
        conn,
        {
            "content_type": draft.content_type,
            "platform": draft.platform,
            "title": draft.title,
            "body": draft.body,
            "hook": draft.hook,
            "source_refs": draft.source_refs,
            "signal_score": draft.signal_score,
            "status": "draft",
            "llm_model": llm_model,
            "generated_at": generated_at,
            "raw_json": draft.model_dump(mode="json"),
        },
    )
