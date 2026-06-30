from dataclasses import dataclass
from datetime import date, datetime, timedelta

from lib.scout.profile import FounderProfile
from lib.schemas import ScoutScores


@dataclass
class RankedOpportunity:
    scores: ScoutScores
    rank_reason: str


def _normalize(text: str) -> str:
    return text.lower()


def _keyword_score(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    normalized = _normalize(text)
    hits = sum(1 for kw in keywords if _normalize(kw) in normalized)
    return min(100.0, (hits / max(len(keywords) * 0.15, 1)) * 100)


def _stage_score(text: str, profile: FounderProfile) -> float:
    stage = profile.company.stage
    stage_keywords = profile.signals.stage_keywords.get(stage, [])
    base = _keyword_score(text, stage_keywords)
    location_bonus = min(20.0, _keyword_score(text, profile.signals.location_keywords) * 0.2)
    return min(100.0, base + location_bonus)


def _deadline_score(deadline_at: date | None) -> float:
    if deadline_at is None:
        return 10.0
    today = date.today()
    days_out = (deadline_at - today).days
    if days_out < 0:
        return 0.0
    if days_out <= 7:
        return 100.0
    if days_out <= 30:
        return 70.0
    if days_out <= 90:
        return 40.0
    return 20.0


def _build_reason(scores: ScoutScores, category: str) -> str:
    highlights: list[str] = []
    if scores.education_focus >= 60:
        highlights.append("EdTech fit")
    if scores.language_preservation >= 50:
        highlights.append("language preservation")
    if scores.ai_focus >= 50:
        highlights.append("AI focus")
    if scores.minority_founder >= 50:
        highlights.append("diverse founder eligibility")
    if scores.stage_fit >= 50:
        highlights.append("pre-seed stage fit")
    if scores.deadline >= 70:
        highlights.append("urgent deadline")

    if highlights:
        return f"Strong {' + '.join(highlights[:3])} ({category.replace('_', ' ')})"
    return f"Moderate match ({category.replace('_', ' ')})"


def rank_opportunity(
    *,
    title: str,
    snippet: str = "",
    description: str | None = None,
    stage: str | None = None,
    category: str = "",
    deadline_at: date | None = None,
    profile: FounderProfile,
) -> RankedOpportunity:
    text = " ".join(filter(None, [title, snippet, description or "", stage or ""]))
    signals = profile.signals
    priorities = profile.priorities

    scores = ScoutScores(
        stage_fit=_stage_score(text, profile),
        ai_focus=_keyword_score(text, signals.ai_keywords),
        education_focus=_keyword_score(text, signals.education_keywords),
        language_preservation=_keyword_score(text, signals.language_preservation_keywords),
        minority_founder=_keyword_score(text, signals.minority_founder_keywords),
        deadline=_deadline_score(deadline_at),
    )

    total = (
        scores.stage_fit * priorities.stage_fit
        + scores.ai_focus * priorities.ai_focus
        + scores.education_focus * priorities.education_focus
        + scores.language_preservation * priorities.language_preservation
        + scores.minority_founder * priorities.minority_founder
        + scores.deadline * priorities.deadlines
    )
    scores.total = round(total, 1)

    return RankedOpportunity(
        scores=scores,
        rank_reason=_build_reason(scores, category),
    )


def parse_deadline_from_text(text: str) -> date | None:
    """Best-effort deadline extraction from search snippets."""
    import re

    normalized = text.lower()
    today = date.today()

    iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    month_names = (
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    )
    for i, month in enumerate(month_names, start=1):
        pattern = rf"\b{month}\s+(\d{{1,2}}),?\s+(20\d{{2}})\b"
        match = re.search(pattern, normalized)
        if match:
            try:
                return date(int(match.group(2)), i, int(match.group(1)))
            except ValueError:
                continue

    if "deadline" in normalized or "apply by" in normalized or "due" in normalized:
        for days in (7, 14, 21, 30):
            if f"{days} day" in normalized:
                return today + timedelta(days=days)

    return None
