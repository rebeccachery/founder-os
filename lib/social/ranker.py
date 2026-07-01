from datetime import date

from lib.schemas import (
    CommitSignal,
    DatasetSignal,
    FeatureSignal,
    MilestoneSignal,
    RankedSignal,
    ReleaseSignal,
    SocialContext,
)
from lib.scout.profile import FounderProfile, load_founder_profile


def _keyword_score(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    normalized = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in normalized)
    return min(3.0, hits * 0.75)


def _profile_keywords(profile: FounderProfile) -> list[str]:
    signals = profile.signals
    return (
        signals.ai_keywords
        + signals.education_keywords
        + signals.language_preservation_keywords
    )


def _rank_commit(commit: CommitSignal, profile: FounderProfile) -> RankedSignal:
    text = commit.subject
    score = 4.0
    reasons: list[str] = []

    if commit.insertions >= 100:
        score += 2.0
        reasons.append("substantial change")
    if commit.files_changed >= 5:
        score += 1.5
        reasons.append(f"{commit.files_changed} files touched")
    keyword_bonus = _keyword_score(text, _profile_keywords(profile))
    if keyword_bonus:
        score += keyword_bonus
        reasons.append("thesis-aligned topic")

    score = min(10.0, score)
    if not reasons:
        reasons.append("recent commit")

    return RankedSignal(
        signal_type="commit",
        signal_key=commit.sha,
        title=commit.subject,
        summary=(
            f"{commit.author} · +{commit.insertions}/-{commit.deletions} "
            f"· {commit.files_changed} files"
        ),
        score=round(score, 1),
        rank_reason=", ".join(reasons),
        source_ref={
            "type": "commit",
            "id": commit.sha,
            "url": commit.url,
        },
    )


def _rank_release(release: ReleaseSignal) -> RankedSignal:
    label = release.name or release.tag
    return RankedSignal(
        signal_type="release",
        signal_key=release.tag,
        title=label,
        summary=release.body[:200] if release.body else f"Release {release.tag}",
        score=9.0 if not release.prerelease else 7.0,
        rank_reason="new release" if not release.prerelease else "pre-release",
        source_ref={
            "type": "release",
            "id": release.tag,
            "url": release.url,
        },
    )


def _rank_milestone(milestone: MilestoneSignal) -> RankedSignal:
    score = 5.0
    reasons: list[str] = []

    if milestone.state == "closed":
        score = 8.5
        reasons.append("milestone completed")
    elif milestone.state in ("in_progress", "open"):
        score = 6.5
        reasons.append("active milestone")
        if milestone.due_on:
            days = (milestone.due_on - date.today()).days
            if 0 <= days <= 14:
                score += 1.0
                reasons.append("due within 2 weeks")

    return RankedSignal(
        signal_type="milestone",
        signal_key=milestone.title,
        title=milestone.title,
        summary=milestone.description or milestone.title,
        score=min(10.0, score),
        rank_reason=", ".join(reasons) or "roadmap milestone",
        source_ref={
            "type": "milestone",
            "id": milestone.title,
            "url": milestone.url,
            "source": milestone.source,
        },
    )


def _rank_feature(feature: FeatureSignal) -> RankedSignal:
    status_scores = {
        "shipped": 8.0,
        "beta": 6.5,
        "in_progress": 5.0,
        "planned": 4.0,
    }
    score = status_scores.get(feature.status, 5.0)
    return RankedSignal(
        signal_type="feature",
        signal_key=feature.name,
        title=feature.name,
        summary=feature.hook or feature.name,
        score=score,
        rank_reason=f"feature ({feature.status})",
        source_ref={
            "type": "feature",
            "id": feature.name,
            "url": feature.url,
        },
    )


def _rank_dataset(dataset: DatasetSignal) -> RankedSignal:
    raw = dataset.score_total or 0.0
    score = min(10.0, raw / 10.0)
    return RankedSignal(
        signal_type="dataset",
        signal_key=dataset.url,
        title=dataset.name,
        summary=dataset.rank_reason or dataset.description or dataset.name,
        score=round(score, 1),
        rank_reason=dataset.rank_reason or f"OSS {dataset.resource_type}",
        source_ref={
            "type": "dataset",
            "id": str(dataset.id or dataset.url),
            "url": dataset.url,
            "resource_type": dataset.resource_type,
        },
    )


def rank_signals(
    context: SocialContext,
    *,
    min_score: float = 6.0,
    max_signals: int = 5,
) -> list[RankedSignal]:
    profile = load_founder_profile()
    ranked: list[RankedSignal] = []

    for commit in context.commits:
        ranked.append(_rank_commit(commit, profile))
    for release in context.releases:
        ranked.append(_rank_release(release))
    for milestone in context.milestones:
        ranked.append(_rank_milestone(milestone))
    for feature in context.features:
        ranked.append(_rank_feature(feature))
    for dataset in context.datasets:
        ranked.append(_rank_dataset(dataset))

    ranked.sort(key=lambda s: s.score, reverse=True)
    above_threshold = [s for s in ranked if s.score >= min_score]

    if above_threshold:
        return above_threshold[:max_signals]

    return ranked[: max(1, min(max_signals, len(ranked)))]
