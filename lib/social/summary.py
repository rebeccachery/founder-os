from lib.schemas import CommitSignal, RankedSignal, SocialContext


def _format_commit_line(commit: CommitSignal) -> str:
    prefix = f"[{commit.repo_name}]"
    line = f"  - {prefix} {commit.subject}"
    if commit.body:
        line += f" — {commit.body[:160]}"
    elif commit.files_changed:
        line += f" (+{commit.insertions}/-{commit.deletions})"
    return line


def summarize_context(context: SocialContext) -> str:
    lines: list[str] = []

    lines.append(
        f"Period: {context.period_start.date()} to {context.period_end.date()}"
    )
    lines.append(f"Company: {context.company_name}")
    lines.append(f"Primary repo: {context.primary_repo or 'none'}")

    if context.repos:
        lines.append("Repo activity:")
        for repo in context.repos:
            angle = f" — {repo.content_angle}" if repo.content_angle else ""
            top = f", top: {repo.top_commit}" if repo.top_commit else ""
            lines.append(
                f"  - {repo.repo_name} ({repo.repo_role}): "
                f"{repo.commit_count} commits via {repo.source}{top}{angle}"
            )

    if context.commits:
        lines.append(f"Commits ({len(context.commits)}):")
        for commit in context.commits[:12]:
            lines.append(_format_commit_line(commit))

    if context.releases:
        lines.append(f"Releases ({len(context.releases)}):")
        for release in context.releases:
            lines.append(
                f"  - [{release.repo_name}] {release.tag}: {release.name or release.tag}"
            )

    if context.milestones:
        lines.append(f"Milestones ({len(context.milestones)}):")
        for milestone in context.milestones:
            repo = f"[{milestone.repo_name}] " if milestone.repo_name else ""
            lines.append(f"  - {repo}{milestone.title} [{milestone.state}]")

    if context.features:
        lines.append(f"Features ({len(context.features)}):")
        for feature in context.features:
            hook = f" — {feature.hook}" if feature.hook else ""
            repo = f"[{feature.repo}] " if feature.repo else ""
            lines.append(f"  - {repo}{feature.name} ({feature.status}){hook}")

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
        repo = signal.source_ref.get("repo")
        repo_label = f" [{repo}]" if repo else ""
        lines.append(
            f"{i}. [{signal.signal_type}]{repo_label} {signal.title} "
            f"(score {signal.score}) — {signal.rank_reason}"
        )
        lines.append(f"   {signal.summary[:200]}")
    return "\n".join(lines)
