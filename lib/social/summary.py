from lib.schemas import RankedSignal, SocialContext


def summarize_context(context: SocialContext) -> str:
    lines: list[str] = []

    lines.append(
        f"Period: {context.period_start.date()} to {context.period_end.date()}"
    )
    lines.append(f"Repo: {context.repo_owner}/{context.repo_name}")

    if context.commits:
        lines.append(f"Commits ({len(context.commits)}):")
        for commit in context.commits[:10]:
            lines.append(
                f"  - {commit.subject} (+{commit.insertions}/-{commit.deletions})"
            )

    if context.releases:
        lines.append(f"Releases ({len(context.releases)}):")
        for release in context.releases:
            lines.append(f"  - {release.tag}: {release.name or release.tag}")

    if context.milestones:
        lines.append(f"Milestones ({len(context.milestones)}):")
        for milestone in context.milestones:
            lines.append(f"  - {milestone.title} [{milestone.state}]")

    if context.features:
        lines.append(f"Features ({len(context.features)}):")
        for feature in context.features:
            hook = f" — {feature.hook}" if feature.hook else ""
            lines.append(f"  - {feature.name} ({feature.status}){hook}")

    if context.datasets:
        lines.append(f"OSS resources ({len(context.datasets)}):")
        for dataset in context.datasets[:5]:
            lines.append(f"  - {dataset.name} (score {dataset.score_total})")

    return "\n".join(lines)


def format_ranked_signals(signals: list[RankedSignal]) -> str:
    if not signals:
        return "No ranked signals."
    lines: list[str] = []
    for i, signal in enumerate(signals, 1):
        lines.append(
            f"{i}. [{signal.signal_type}] {signal.title} "
            f"(score {signal.score}) — {signal.rank_reason}"
        )
        lines.append(f"   {signal.summary[:200]}")
    return "\n".join(lines)
