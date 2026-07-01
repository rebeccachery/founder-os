from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.database import db_session
from api.deps import verify_api_key
from lib.assistant.briefing import briefing_needs_rebuild, briefing_to_db_row, build_briefing
from lib.db import (
    attach_scout_track_flags,
    delete_assistant_track,
    ensure_assistant_track,
    get_application_draft,
    get_assistant_track,
    get_briefing,
    get_deadlines,
    get_scout_opportunity,
    get_social_post,
    get_stats,
    list_oss_resources,
    list_scout_opportunities,
    list_social_posts,
    list_table,
    update_social_post_status,
    upsert_application_draft,
    upsert_assistant_track,
    upsert_briefing,
)
from lib.discovery.profile import load_oss_profile
from lib.opportunities.intake import save_opportunity
from lib.opportunities.update import update_scout_deadline
from lib.schemas import (
    ApplicationDraft,
    ApplicationDraftUpdate,
    AssistantTrack,
    AssistantTrackUpdate,
    SavedOpportunity,
    SavedOpportunityCreate,
    ScoutOpportunityUpdate,
)

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/investors")
def get_investors(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_table(conn, "investors", status=status, limit=limit)


def _track_to_model(row: dict) -> AssistantTrack:
    return AssistantTrack(
        source_table=row["source_table"],
        source_id=int(row["source_id"]),
        pin_priority=bool(row["pin_priority"]),
        track_application=bool(row["track_application"]),
        dismissed_until=row.get("dismissed_until"),
        updated_at=row.get("updated_at"),
    )


@router.get("/scout")
def get_scout(
    status: str | None = None,
    category: str | None = None,
    source: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    exclude_tracked: bool = Query(default=False),
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        rows = list_scout_opportunities(
            conn,
            status=status,
            category=category,
            source=source,
            min_score=min_score,
            exclude_tracked=exclude_tracked,
            limit=limit,
        )
        return attach_scout_track_flags(conn, rows)


@router.post("/opportunities/saved", response_model=SavedOpportunity)
def save_opportunity_route(
    payload: SavedOpportunityCreate,
    _: None = Depends(verify_api_key),
):
    if not payload.url and not payload.description:
        raise HTTPException(
            status_code=400,
            detail="Provide an application URL or paste tweet text with a link.",
        )
    try:
        with db_session() as conn:
            row = save_opportunity(conn, payload)
            ensure_assistant_track(conn, row["id"], track_application=True)
            briefing = build_briefing(conn)
            upsert_briefing(conn, briefing_to_db_row(briefing))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SavedOpportunity(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        url=row.get("url"),
        deadline_at=row.get("deadline_at"),
        status=row.get("status", "new"),
        source=row.get("source"),
        score_total=row.get("score_total"),
        rank_reason=row.get("rank_reason"),
        description=row.get("description"),
        created=row.get("created", True),
    )


@router.patch("/scout/{opportunity_id}")
def update_scout_opportunity_route(
    opportunity_id: int,
    payload: ScoutOpportunityUpdate,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        if not get_scout_opportunity(conn, opportunity_id):
            raise HTTPException(status_code=404, detail="Scout opportunity not found")
        try:
            row = update_scout_deadline(conn, opportunity_id, payload.deadline_at)
            briefing = build_briefing(conn)
            upsert_briefing(conn, briefing_to_db_row(briefing))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return row


@router.get("/assistant/tracks", response_model=list[AssistantTrack])
def list_assistant_tracks_route(_: None = Depends(verify_api_key)):
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT source_table, source_id, pin_priority, track_application,
                   dismissed_until, updated_at
            FROM assistant_tracks
            WHERE source_table = 'scout_opportunities'
            ORDER BY updated_at DESC
            """
        ).fetchall()
        return [_track_to_model(dict(row)) for row in rows]


@router.put("/assistant/tracks/{source_id}", response_model=AssistantTrack)
def upsert_assistant_track_route(
    source_id: int,
    payload: AssistantTrackUpdate,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        try:
            row = upsert_assistant_track(
                conn,
                source_id,
                pin_priority=payload.pin_priority,
                track_application=payload.track_application,
                dismissed_until=(
                    payload.dismissed_until.isoformat() if payload.dismissed_until else None
                ),
                clear_dismissed=payload.clear_dismissed,
            )
            briefing = build_briefing(conn)
            upsert_briefing(conn, briefing_to_db_row(briefing))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _track_to_model(row)


@router.delete("/assistant/tracks/{source_id}")
def delete_assistant_track_route(
    source_id: int,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        if not get_assistant_track(conn, source_id):
            raise HTTPException(status_code=404, detail="Track not found")
        delete_assistant_track(conn, source_id)
        briefing = build_briefing(conn)
        upsert_briefing(conn, briefing_to_db_row(briefing))
    return {"ok": True}


@router.get("/applications/{source_table}/{source_id}/draft", response_model=ApplicationDraft)
def get_application_draft_route(
    source_table: str,
    source_id: int,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        draft = get_application_draft(conn, source_table, source_id)
        if not draft:
            return ApplicationDraft(source_table=source_table, source_id=source_id, body="")
        return ApplicationDraft(
            source_table=draft["source_table"],
            source_id=draft["source_id"],
            body=draft["body"],
            updated_at=draft.get("updated_at"),
        )


@router.put("/applications/{source_table}/{source_id}/draft", response_model=ApplicationDraft)
def save_application_draft_route(
    source_table: str,
    source_id: int,
    payload: ApplicationDraftUpdate,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        try:
            draft = upsert_application_draft(conn, source_table, source_id, payload.body)
            briefing = build_briefing(conn)
            upsert_briefing(conn, briefing_to_db_row(briefing))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApplicationDraft(
        source_table=draft["source_table"],
        source_id=draft["source_id"],
        body=draft["body"],
        updated_at=draft.get("updated_at"),
    )


@router.get("/oss")
def get_oss(
    status: str | None = None,
    resource_type: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    view: str = Query(default="recent", pattern="^(recent|reference|all)$"),
    recent_days: int | None = Query(default=None, ge=1, le=365),
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    profile = load_oss_profile()
    days = recent_days if recent_days is not None else profile.recency.digest_recent_days
    with db_session() as conn:
        return list_oss_resources(
            conn,
            status=status,
            resource_type=resource_type,
            min_score=min_score,
            view=view,
            recent_days=days,
            limit=limit,
        )


@router.get("/deadlines")
def get_deadlines_route(
    days: int = Query(default=30, ge=1, le=365),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return get_deadlines(conn, days=days)


@router.get("/briefing")
def get_briefing_route(
    briefing_date: str | None = Query(default=None, alias="date"),
    _: None = Depends(verify_api_key),
):
    target = briefing_date or date.today().isoformat()
    with db_session() as conn:
        row = get_briefing(conn, target)
        if row and not briefing_needs_rebuild(row):
            return row
        briefing = build_briefing(conn, date.fromisoformat(target))
        upsert_briefing(conn, briefing_to_db_row(briefing))
        return get_briefing(conn, target)


@router.get("/contacts")
def get_contacts(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_table(conn, "contacts", status=status, limit=limit)


@router.get("/stats")
def get_stats_route(_: None = Depends(verify_api_key)):
    with db_session() as conn:
        return get_stats(conn)


class SocialPostUpdate(BaseModel):
    status: str = Field(pattern="^(draft|approved|posted|skipped|archived)$")
    body: str | None = None


@router.get("/social")
def get_social_posts(
    status: str | None = Query(default=None, pattern="^(draft|approved|posted|skipped|archived)$"),
    content_type: str | None = None,
    limit: int = Query(default=50, le=200),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_social_posts(
            conn,
            status=status,
            content_type=content_type,
            limit=limit,
        )


@router.get("/social/{post_id}")
def get_social_post_route(
    post_id: int,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        row = get_social_post(conn, post_id)
        if not row:
            raise HTTPException(status_code=404, detail="Social post not found")
        return row


@router.patch("/social/{post_id}")
def update_social_post_route(
    post_id: int,
    payload: SocialPostUpdate,
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        if not get_social_post(conn, post_id):
            raise HTTPException(status_code=404, detail="Social post not found")
        update_social_post_status(
            conn,
            post_id,
            payload.status,
            body=payload.body,
        )
        return get_social_post(conn, post_id)
