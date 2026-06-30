from fastapi import APIRouter, Depends, Query

from api.database import db_session
from api.deps import verify_api_key
from lib.db import get_deadlines, get_stats, list_oss_resources, list_scout_opportunities, list_table, seed_demo_data
from lib.discovery.profile import load_oss_profile

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
    min_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=100, le=500),
    _: None = Depends(verify_api_key),
):
    with db_session() as conn:
        return list_scout_opportunities(
            conn,
            status=status,
            category=category,
            min_score=min_score,
            limit=limit,
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
