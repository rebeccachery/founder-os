import os
from pathlib import Path

from lib.llm.client import LlmError, chat_json, is_llm_available
from lib.schemas import RankedSignal, SocialContext, SocialDraft, SocialGenerationResult
from lib.scout.profile import load_founder_profile
from lib.social.profile import load_social_profile
from lib.social.ranker import rank_signals
from lib.social.summary import format_ranked_signals, summarize_context

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents" / "social" / "prompts"

CONTENT_TYPE_LABELS = {
    "twitter_thread": "Twitter thread",
    "linkedin_post": "LinkedIn post",
    "demo_idea": "Demo idea",
    "launch_announcement": "Launch announcement",
}


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def _top_signal(signals: list[RankedSignal]) -> RankedSignal | None:
    return signals[0] if signals else None


def _source_refs(signal: RankedSignal | None) -> list[dict]:
    if not signal:
        return []
    return [signal.source_ref]


def _template_drafts(
    context: SocialContext,
    signals: list[RankedSignal],
    profile,
) -> list[SocialDraft]:
    top = _top_signal(signals)
    company = context.company_name or "Our startup"
    cta = profile.voice.cta_url or f"https://github.com/{context.repo_owner}/{context.repo_name}"
    hashtags = " ".join(f"#{tag}" for tag in profile.voice.hashtags[:3])
    topic = top.title if top else company
    hook_text = top.summary if top else context.features[0].hook if context.features else company

    weekly_lines: list[str] = []
    if context.commits:
        weekly_lines.append(f"{len(context.commits)} commit(s)")
    if context.features:
        shipped = [f.name for f in context.features if f.status == "shipped"]
        if shipped:
            weekly_lines.append(f"shipped: {', '.join(shipped[:2])}")
    if context.datasets:
        weekly_lines.append(f"indexed {len(context.datasets)} OSS resource(s)")

    weekly_summary = ", ".join(weekly_lines) if weekly_lines else "steady progress on the product"

    drafts = [
        SocialDraft(
            content_type="twitter_thread",
            platform="twitter",
            title=f"Build update: {topic[:50]}",
            hook=f"This week at {company}: {weekly_summary}.",
            body="\n".join(
                [
                    f"1/ This week at {company}: {weekly_summary}.",
                    f"2/ Highlight: {topic} — {hook_text[:200]}",
                    f"3/ Why it matters: we're building for underresourced languages in EdTech.",
                    f"4/ Follow along: {cta}",
                ]
            ),
            source_refs=_source_refs(top),
            signal_score=top.score if top else None,
        ),
        SocialDraft(
            content_type="linkedin_post",
            platform="linkedin",
            title=f"Weekly update — {topic[:40]}",
            hook=f"A quick update from {company}.",
            body=(
                f"A quick update from {company}.\n\n"
                f"This period: {weekly_summary}.\n\n"
                f"The thread I'm most excited about: {topic}. {hook_text}\n\n"
                f"We're pre-seed, NYC-based, focused on translation and pronunciation "
                f"for underresourced languages.\n\n"
                f"More: {cta}\n\n{hashtags}"
            ),
            source_refs=_source_refs(top),
            signal_score=top.score if top else None,
        ),
        SocialDraft(
            content_type="demo_idea",
            platform="internal",
            title=f"60s demo: {topic[:40]}",
            hook=f"Show how {topic} works in under 60 seconds.",
            body=(
                f"**Problem:** Founders struggle to explain {topic} quickly.\n\n"
                f"**Demo script:**\n"
                f"1. Open the dashboard (5s)\n"
                f"2. Show the signal that triggered this week: {topic} (20s)\n"
                f"3. Walk through one concrete output (25s)\n"
                f"4. Close with CTA: {cta} (10s)\n\n"
                f"**Recording tip:** Screen record with your face cam in the corner; "
                f"keep narration conversational, not scripted."
            ),
            source_refs=_source_refs(top),
            signal_score=top.score if top else None,
        ),
        SocialDraft(
            content_type="launch_announcement",
            platform="both",
            title=f"Progress update: {topic[:40]}",
            hook=f"{company} — progress update",
            body=(
                f"**{company} — progress update**\n\n"
                f"What we worked on: {weekly_summary}.\n\n"
                f"Spotlight: {topic}. {hook_text}\n\n"
                f"Why it matters: building tools for language learning and preservation.\n\n"
                f"Follow the build: {cta}"
            ),
            source_refs=_source_refs(top),
            signal_score=top.score if top else None,
        ),
    ]

    allowed = set(profile.generation.content_types)
    return [draft for draft in drafts if draft.content_type in allowed]


def _llm_drafts(
    context: SocialContext,
    signals: list[RankedSignal],
    profile,
) -> list[SocialDraft]:
    founder = load_founder_profile()
    system = _load_prompt("system.txt")
    template = _load_prompt("generate.txt")

    user = template.format(
        company_name=context.company_name or founder.company.name,
        company_stage=context.company_stage or founder.company.stage,
        company_description=founder.company.description.strip(),
        tone=profile.voice.tone,
        hashtags=", ".join(profile.voice.hashtags),
        avoid=", ".join(profile.voice.avoid),
        cta_url=profile.voice.cta_url
        or f"https://github.com/{context.repo_owner}/{context.repo_name}",
        signals_summary=format_ranked_signals(signals),
        context_summary=summarize_context(context),
    )

    provider = profile.llm.provider
    model = profile.llm.model
    if os.getenv("LLM_MODEL"):
        model = os.getenv("LLM_MODEL", model)

    payload = chat_json(
        system=system,
        user=user,
        model=model,
        provider=provider,
        temperature=profile.llm.temperature,
        base_url=profile.llm.base_url,
    )

    drafts: list[SocialDraft] = []
    top_score = signals[0].score if signals else None
    for item in payload.get("drafts", []):
        content_type = item.get("content_type", "")
        if content_type not in profile.generation.content_types:
            continue
        drafts.append(
            SocialDraft(
                content_type=content_type,
                platform=item.get("platform", "internal"),
                title=item.get("title", CONTENT_TYPE_LABELS.get(content_type, content_type)),
                hook=item.get("hook", ""),
                body=item.get("body", ""),
                source_refs=item.get("source_refs") or _source_refs(_top_signal(signals)),
                signal_score=top_score,
            )
        )
    return drafts


def generate_social_content(context: SocialContext) -> SocialGenerationResult:
    profile = load_social_profile()
    signals = rank_signals(
        context,
        min_score=profile.generation.min_signal_score,
        max_signals=profile.generation.max_signals,
    )

    llm_provider = os.getenv("LLM_PROVIDER", profile.llm.provider)
    llm_model = os.getenv("LLM_MODEL", profile.llm.model)

    if is_llm_available(llm_provider, profile.llm.base_url):
        try:
            drafts = _llm_drafts(context, signals, profile)
            if drafts:
                return SocialGenerationResult(
                    ranked_signals=signals,
                    drafts=drafts,
                    llm_used=True,
                    llm_model=f"{llm_provider}/{llm_model}",
                )
        except LlmError:
            pass

    return SocialGenerationResult(
        ranked_signals=signals,
        drafts=_template_drafts(context, signals, profile),
        llm_used=False,
        llm_model=None,
    )
