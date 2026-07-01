import json
from datetime import date, datetime, timedelta

import sqlite3

from lib.db import get_last_agent_run, list_oss_resources
from lib.schemas import (
    DatasetSignal,
    FeatureSignal,
    MilestoneSignal,
    SocialContext,
)
from lib.scout.profile import load_founder_profile
from lib.social.profile import load_features_config, load_social_profile, primary_repo
from lib.social.repos import collect_all_repos


def _period_start(conn: sqlite3.Connection, since_days: int) -> datetime:
    last_run = get_last_agent_run(conn, "social")
    if last_run:
        return last_run
    return datetime.utcnow() - timedelta(days=since_days)


def _load_features() -> list[FeatureSignal]:
    config = load_features_config()
    features: list[FeatureSignal] = []
    for item in config.features:
        shipped_at = None
        if item.shipped_at:
            shipped_at = (
                item.shipped_at
                if isinstance(item.shipped_at, date)
                else date.fromisoformat(item.shipped_at)
            )
        features.append(
            FeatureSignal(
                name=item.name,
                status=item.status,
                hook=item.hook,
                shipped_at=shipped_at,
                url=item.url,
                repo=item.repo,
            )
        )
    return features


def _load_manual_milestones() -> list[MilestoneSignal]:
    config = load_features_config()
    milestones: list[MilestoneSignal] = []
    for item in config.milestones:
        due_on = None
        if item.target_date:
            due_on = (
                item.target_date
                if isinstance(item.target_date, date)
                else date.fromisoformat(item.target_date)
            )
        milestones.append(
            MilestoneSignal(
                title=item.name,
                description=item.description,
                state=item.status,
                due_on=due_on,
                source="manual",
                repo_name=item.repo or "",
            )
        )
    return milestones


def _load_datasets(conn: sqlite3.Connection) -> list[DatasetSignal]:
    profile = load_social_profile()
    cfg = profile.datasets
    datasets: list[DatasetSignal] = []

    for resource_type in cfg.resource_types:
        rows = list_oss_resources(
            conn,
            resource_type=resource_type,
            min_score=cfg.min_score,
            view="recent",
            recent_days=cfg.recent_days,
            limit=cfg.limit,
        )
        for row in rows:
            discovered_at = None
            if row.get("discovered_at"):
                discovered_at = datetime.fromisoformat(row["discovered_at"])
            datasets.append(
                DatasetSignal(
                    id=row.get("id"),
                    name=row["name"],
                    url=row["url"],
                    description=row.get("description"),
                    score_total=row.get("score_total"),
                    rank_reason=row.get("rank_reason"),
                    resource_type=row["resource_type"],
                    discovered_at=discovered_at,
                )
            )

    datasets.sort(key=lambda d: d.score_total or 0, reverse=True)
    return datasets[: cfg.limit]


def collect_social_context(conn: sqlite3.Connection) -> SocialContext:
    social_profile = load_social_profile()
    founder_profile = load_founder_profile()
    period_end = datetime.utcnow()
    period_start = _period_start(conn, social_profile.since_days)

    commits, releases, github_milestones, repo_summaries = collect_all_repos(
        social_profile,
        period_start,
    )
    milestones = _load_manual_milestones() + github_milestones

    main = primary_repo(social_profile)
    company_name = social_profile.voice.company_name or founder_profile.company.name

    return SocialContext(
        period_start=period_start,
        period_end=period_end,
        commits=commits,
        releases=releases,
        milestones=milestones,
        features=_load_features(),
        datasets=_load_datasets(conn),
        repos=repo_summaries,
        company_name=company_name,
        company_stage=founder_profile.company.stage,
        primary_repo=main.name if main else "",
        repo_owner=main.owner if main else "",
        repo_name=main.name if main else "",
    )


def context_to_json(context: SocialContext) -> str:
    return json.dumps(context.model_dump(mode="json"), indent=2)
