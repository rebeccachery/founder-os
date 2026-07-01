import os
from pathlib import Path

from lib.llm.client import LlmError, chat_json, is_llm_available
from lib.schemas import RankedSignal, SocialContext, SocialDraft, SocialGenerationResult
from lib.scout.profile import load_founder_profile
from lib.social.profile import load_social_profile
from lib.social.ranker import rank_signals, signal_for_repo
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


def _weekly_summary(context: SocialContext) -> str:
    lines: list[str] = []
    for repo in context.repos:
        if repo.commit_count:
            lines.append(f"{repo.repo_name}: {repo.commit_count} commit(s)")
    if context.features:
        shipped = [f.name for f in context.features if f.status == "shipped"]
        if shipped:
            lines.append(f"shipped: {', '.join(shipped[:2])}")
    return ", ".join(lines) if lines else "steady progress on Your Company"


def _template_drafts(
    context: SocialContext,
    signals: list[RankedSignal],
    profile,
) -> list[SocialDraft]:
    primary = signal_for_repo(signals, "your-product-repo") or _top_signal(signals)
    map_signal = signal_for_repo(signals, "nyc_map") or primary
    demo_signal = signal_for_repo(signals, "your-product-demo") or primary

    company = profile.voice.company_name or context.company_name or "Your Company"
    cta = profile.voice.cta_url or "https://example.com/"
    hashtags = " ".join(f"#{tag}" for tag in profile.voice.hashtags[:3])
    weekly_summary = _weekly_summary(context)

    drafts = [
        SocialDraft(
            content_type="twitter_thread",
            platform="twitter",
            title=f"NYC map update: {(map_signal.title if map_signal else company)[:40]}",
            hook=f"Mapping Haitian community strength and education gaps in NYC.",
            body="\n".join(
                [
                    f"1/ We're building {company} for underresourced languages — and mapping where support is needed most.",
                    f"2/ This week on nyc_map: {(map_signal.title if map_signal else 'map improvements')}. {map_signal.summary[:180] if map_signal else ''}",
                    f"3/ Why it matters: language learning tools should meet communities where they are.",
                    f"4/ Explore Your Company: {cta}",
                ]
            ),
            source_refs=_source_refs(map_signal),
            signal_score=map_signal.score if map_signal else None,
        ),
        SocialDraft(
            content_type="linkedin_post",
            platform="linkedin",
            title=f"Your Company weekly — {(primary.title if primary else company)[:40]}",
            hook=f"A quick update from {company}.",
            body=(
                f"A quick update from {company}.\n\n"
                f"This period: {weekly_summary}.\n\n"
                f"Product focus: {(primary.title if primary else 'platform work')}. "
                f"{primary.summary[:240] if primary else ''}\n\n"
                f"We're building pronunciation and translation feedback for underresourced languages — "
                f"starting with Haitian Creole.\n\n"
                f"Learn more: {cta}\n\n{hashtags}"
            ),
            source_refs=_source_refs(primary),
            signal_score=primary.score if primary else None,
        ),
        SocialDraft(
            content_type="demo_idea",
            platform="internal",
            title=f"60s demo: {(demo_signal.title if demo_signal else 'Your Company prototype')[:40]}",
            hook="Record a short walkthrough for the landing page demo slot.",
            body=(
                f"**Problem:** Prospects need to see Your Company, not read about it.\n\n"
                f"**Demo script (60s):**\n"
                f"1. Open your-product-demo or landing page ({cta}) (5s)\n"
                f"2. Show: {(demo_signal.title if demo_signal else 'speaking feedback prototype')} (25s)\n"
                f"3. One sentence on Haitian Creole / underresourced languages (15s)\n"
                f"4. CTA: demo video coming soon — join the waitlist at {cta} (15s)\n\n"
                f"**Tip:** Face cam + screen; conversational, not scripted."
            ),
            source_refs=_source_refs(demo_signal),
            signal_score=demo_signal.score if demo_signal else None,
        ),
        SocialDraft(
            content_type="launch_announcement",
            platform="both",
            title=f"Your Company progress — {(primary.title if primary else company)[:40]}",
            hook=f"{company} — progress update",
            body=(
                f"**{company} — progress update**\n\n"
                f"What we worked on: {weekly_summary}.\n\n"
                f"Spotlight: {(primary.title if primary else 'platform improvements')}. "
                f"{primary.summary[:200] if primary else ''}\n\n"
                f"Building for language learning and preservation. Demo video coming soon.\n\n"
                f"{cta}"
            ),
            source_refs=_source_refs(primary),
            signal_score=primary.score if primary else None,
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
        company_name=profile.voice.company_name or context.company_name or founder.company.name,
        company_stage=context.company_stage or founder.company.stage,
        company_description=founder.company.description.strip(),
        tone=profile.voice.tone,
        hashtags=", ".join(profile.voice.hashtags),
        avoid=", ".join(profile.voice.avoid),
        cta_url=profile.voice.cta_url or "https://example.com/",
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
