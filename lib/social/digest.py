from datetime import datetime
from pathlib import Path

from lib.schemas import SocialContext, SocialGenerationResult

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "reports"

CONTENT_MENU = [
    ("Monday", "linkedin_post", "Biggest signal from the week"),
    ("Tuesday", "twitter_thread", "Technical deep-dive"),
    ("Wednesday", "demo_idea", "Record a 60s Loom"),
    ("Thursday", "twitter_thread", "Quick win or milestone progress"),
    ("Friday", "launch_announcement", "Release or weekly recap"),
]

CONTENT_TYPE_LABELS = {
    "twitter_thread": "Twitter thread",
    "linkedin_post": "LinkedIn post",
    "demo_idea": "Demo idea",
    "launch_announcement": "Launch announcement",
}


def write_context_digest(context: SocialContext) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    digest_path = REPORTS_DIR / f"social_context_{today}.md"
    json_path = REPORTS_DIR / f"social_context_{today}.json"

    lines = [
        f"# Social Context — {today}\n\n",
        f"**Company:** {context.company_name} ({context.company_stage})\n",
        f"**Primary repo:** {context.primary_repo or '—'}\n",
        f"**Period:** {context.period_start.date()} → {context.period_end.date()}\n\n",
    ]

    lines.append("## Activity by repo\n\n")
    if context.repos:
        lines.append("| Repo | Role | Commits | Source | Top change |\n")
        lines.append("|------|------|---------|--------|------------|\n")
        for repo in context.repos:
            top = repo.top_commit or "—"
            if len(top) > 50:
                top = top[:47] + "..."
            lines.append(
                f"| {repo.repo_name} | {repo.repo_role} | {repo.commit_count} | "
                f"{repo.source} | {top} |\n"
            )
    else:
        lines.append("_No repos configured._\n")
    lines.append("\n")

    lines.append("## Commits\n\n")
    if context.commits:
        current_repo = ""
        for commit in context.commits:
            if commit.repo_name != current_repo:
                current_repo = commit.repo_name
                lines.append(f"### {current_repo}\n\n")
            stats = ""
            if commit.files_changed:
                stats = f" (+{commit.insertions}/-{commit.deletions}, {commit.files_changed} files)"
            body = f"\n  - {commit.body}" if commit.body else ""
            lines.append(
                f"- `{commit.sha[:7]}` **{commit.subject}** — {commit.author}{stats}{body}\n"
            )
    else:
        lines.append("_No commits in this period._\n")
    lines.append("\n")

    lines.append("## Releases\n\n")
    if context.releases:
        for release in context.releases:
            label = release.name or release.tag
            lines.append(
                f"- **[{release.repo_name}]** {label} (`{release.tag}`) — "
                f"{release.published_at.date()}\n"
            )
    else:
        lines.append("_No releases in this period._\n")
    lines.append("\n")

    lines.append("## Milestones\n\n")
    if context.milestones:
        for milestone in context.milestones:
            due = f", due {milestone.due_on}" if milestone.due_on else ""
            lines.append(
                f"- **{milestone.title}** [{milestone.state}] ({milestone.source}{due})\n"
            )
            if milestone.description:
                lines.append(f"  - {milestone.description.strip()}\n")
    else:
        lines.append("_No milestones configured._\n")
    lines.append("\n")

    lines.append("## Features\n\n")
    if context.features:
        for feature in context.features:
            hook = f" — {feature.hook}" if feature.hook else ""
            repo = f"**[{feature.repo}]** " if feature.repo else ""
            lines.append(f"- {repo}**{feature.name}** ({feature.status}){hook}\n")
    else:
        lines.append("_No features in config/features.yaml._\n")
    lines.append("\n")

    lines.append("## Datasets & OSS\n\n")
    if context.datasets:
        for dataset in context.datasets:
            score = f"{dataset.score_total:.1f}" if dataset.score_total is not None else "—"
            lines.append(
                f"- **{dataset.name}** ({dataset.resource_type}, score {score})\n"
            )
            lines.append(f"  - {dataset.url}\n")
            if dataset.rank_reason:
                lines.append(f"  - Why: {dataset.rank_reason}\n")
    else:
        lines.append("_No recent OSS resources above score threshold._\n")
    lines.append("\n")

    digest_path.write_text("".join(lines))
    json_path.write_text(context.model_dump_json(indent=2))
    return digest_path, json_path


def write_content_digest(
    context: SocialContext,
    generation: SocialGenerationResult,
) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    digest_path = REPORTS_DIR / f"social_{today}.md"
    json_path = REPORTS_DIR / f"social_{today}.json"

    llm_note = (
        f"Generated with {generation.llm_model}"
        if generation.llm_used and generation.llm_model
        else "Generated with template fallback (set OPENAI_API_KEY for LLM drafts)"
    )

    lines = [
        f"# Social Content — {today}\n\n",
        f"**Company:** {context.company_name} ({context.company_stage})\n",
        f"**Period:** {context.period_start.date()} → {context.period_end.date()}\n",
        f"*{llm_note}*\n\n",
    ]

    lines.append("## Content menu\n\n")
    lines.append("| Day | Type | Suggestion |\n")
    lines.append("|-----|------|------------|\n")
    for day, content_type, suggestion in CONTENT_MENU:
        label = CONTENT_TYPE_LABELS.get(content_type, content_type)
        lines.append(f"| {day} | {label} | {suggestion} |\n")
    lines.append("\n")

    lines.append("## Top signals\n\n")
    if generation.ranked_signals:
        for signal in generation.ranked_signals:
            repo = signal.source_ref.get("repo")
            repo_label = f" [{repo}]" if repo else ""
            lines.append(
                f"- **[{signal.score}]**{repo_label} {signal.title} ({signal.signal_type}) — "
                f"{signal.rank_reason}\n"
            )
    else:
        lines.append("_No signals ranked._\n")
    lines.append("\n")

    drafts_by_type = {draft.content_type: draft for draft in generation.drafts}
    for content_type, label in CONTENT_TYPE_LABELS.items():
        draft = drafts_by_type.get(content_type)
        lines.append(f"## {label}\n\n")
        if draft:
            lines.append(f"**Title:** {draft.title}\n\n")
            lines.append(f"**Hook:** {draft.hook}\n\n")
            lines.append(f"{draft.body}\n\n")
            if draft.source_refs:
                refs = ", ".join(
                    f"{ref.get('type', '?')}: {ref.get('id', ref.get('title', ''))}"
                    for ref in draft.source_refs
                )
                lines.append(f"_Sources: {refs}_\n\n")
        else:
            lines.append("_No draft generated for this type._\n\n")

    digest_path.write_text("".join(lines))
    json_path.write_text(generation.model_dump_json(indent=2))
    return digest_path, json_path
