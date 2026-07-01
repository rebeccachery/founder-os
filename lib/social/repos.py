from datetime import datetime

from lib.git.collector import (
    collect_repo_commits,
    fetch_github_milestones,
    fetch_github_releases,
    tag_milestone,
    tag_release,
)
from lib.schemas import CommitSignal, MilestoneSignal, ReleaseSignal, RepoActivitySummary
from lib.social.profile import ProductRepoConfig, SocialProfile, resolve_repo_local_path


def collect_all_repos(
    profile: SocialProfile,
    since: datetime,
) -> tuple[list[CommitSignal], list[ReleaseSignal], list[MilestoneSignal], list[RepoActivitySummary]]:
    commits: list[CommitSignal] = []
    releases: list[ReleaseSignal] = []
    milestones: list[MilestoneSignal] = []
    summaries: list[RepoActivitySummary] = []

    excluded = set(profile.exclude_repos)

    for cfg in profile.repos:
        if cfg.name in excluded:
            continue

        repo_path = resolve_repo_local_path(cfg)
        repo_commits, source = collect_repo_commits(
            cfg,
            repo_path,
            since,
            prefer_local_git=profile.github.prefer_local_git,
        )
        commits.extend(repo_commits)

        repo_releases: list[ReleaseSignal] = []
        if cfg.fetch_releases:
            repo_releases = [
                tag_release(r, cfg)
                for r in fetch_github_releases(cfg.owner, cfg.name, since)
            ]
            releases.extend(repo_releases)

        if cfg.fetch_milestones:
            milestones.extend(
                tag_milestone(m, cfg)
                for m in fetch_github_milestones(cfg.owner, cfg.name)
            )

        top_commit = repo_commits[0].subject if repo_commits else None
        summaries.append(
            RepoActivitySummary(
                repo_owner=cfg.owner,
                repo_name=cfg.name,
                repo_role=cfg.role,
                commit_count=len(repo_commits),
                top_commit=top_commit,
                source=source if cfg.fetch_commits else "skipped",
                content_angle=cfg.content_angle,
                repo_url=f"https://github.com/{cfg.owner}/{cfg.name}",
            )
        )

    commits.sort(key=lambda c: c.committed_at, reverse=True)
    releases.sort(key=lambda r: r.published_at, reverse=True)
    return commits, releases, milestones, summaries
