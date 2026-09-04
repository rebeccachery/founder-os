import re
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


_MONTH_NAMES = (
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

_ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_MONTH_DATE_RE = re.compile(
    r"\b(" + "|".join(_MONTH_NAMES) + r")\s+(\d{1,2}),?\s+(20\d{2})\b"
)

# Phrases that indicate a nearby date is actually an application deadline,
# as opposed to a publish date, an image caption, or an unrelated event date
# picked up from a noisy search snippet.
DEADLINE_KEYWORDS = (
    "deadline",
    "apply by",
    "apply before",
    "applications close",
    "applications due",
    "application closes",
    "application deadline",
    "due by",
    "submission deadline",
    "submit by",
    "closes on",
    "close on",
    "closing on",
    "closing date",
    "must apply by",
    "open through",
    "open until",
)

_PROXIMITY_WINDOW = 80


def _date_candidates(text: str) -> list[tuple[int, int, date]]:
    """All (start, end, date) matches for ISO and month-name date patterns."""
    candidates: list[tuple[int, int, date]] = []
    for m in _ISO_DATE_RE.finditer(text):
        try:
            candidates.append(
                (m.start(), m.end(), date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            )
        except ValueError:
            continue
    for m in _MONTH_DATE_RE.finditer(text.lower()):
        month_index = _MONTH_NAMES.index(m.group(1)) + 1
        try:
            candidates.append(
                (m.start(), m.end(), date(int(m.group(3)), month_index, int(m.group(2))))
            )
        except ValueError:
            continue
    return candidates


def _span_gap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    if a_end <= b_start:
        return b_start - a_end
    if b_end <= a_start:
        return a_start - b_end
    return 0


def parse_deadline_from_text(text: str) -> date | None:
    """Extract a deadline date — but only one that appears near deadline-indicating
    language (e.g. "deadline", "apply by", "closes on").

    A date found anywhere else in a search snippet (an image caption, a publish
    date, an unrelated event mentioned in the same page) is not trustworthy
    enough to store as the application deadline, so it's treated as unknown
    rather than guessed.
    """
    normalized = text.lower()
    today = date.today()

    keyword_spans = [
        (m.start(), m.end())
        for kw in DEADLINE_KEYWORDS
        for m in re.finditer(re.escape(kw), normalized)
    ]
    if not keyword_spans:
        return None

    best_gap: int | None = None
    best_date: date | None = None
    for start, end, parsed in _date_candidates(text):
        gap = min(_span_gap(start, end, kw_start, kw_end) for kw_start, kw_end in keyword_spans)
        if gap <= _PROXIMITY_WINDOW and (best_gap is None or gap < best_gap):
            best_gap = gap
            best_date = parsed
    if best_date is not None:
        return best_date

    for days in (7, 14, 21, 30):
        if f"{days} day" in normalized:
            return today + timedelta(days=days)

    return None
