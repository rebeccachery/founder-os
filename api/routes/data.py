from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.database import db_session
from api.deps import verify_api_key
from lib.assistant.briefing import briefing_to_db_row, build_briefing
from lib.db import (
    get_briefing,
    get_deadlines,
    get_stats,
    get_social_post,
    list_oss_resources,
    list_scout_opportunities,
    list_social_posts,
    list_table,
    seed_demo_data,
    update_social_post_status,
    upsert_briefing,
)
from lib.discovery.profile import load_oss_profile
from lib.opportunities.intake import save_opportunity
from lib.schemas import SavedOpportunity, SavedOpportunityCreate

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/investors")
def get_investors(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_table(conn, "investors", status=status, limit=limit)


@router.get("/funding")
def get_funding(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_table(conn, "funding_opportunities", status=status, limit=limit)


@router.get("/grants")
def get_grants(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_table(conn, "grants", status=status, limit=limit)


@router.get("/competitions")
def get_competitions(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_table(conn, "competitions", status=status, limit=limit)


@router.get("/scout")
def get_scout(
    status: str | None = None,
    category: str | None = None,
    source: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_scout_opportunities(
            conn,
            status=status,
            category=category,
            source=source,
            min_score=min_score,
            limit=limit,
        )


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
        if row:
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
