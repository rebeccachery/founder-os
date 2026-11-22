import re
from dataclasses import dataclass
from datetime import date

from lib.schemas import ScoutScores
from lib.scout.actionability import assess_title
from lib.scout.profile import FounderProfile
from lib.text import Matcher, keyword_hits, keyword_score


@dataclass
class RankedOpportunity:
    scores: ScoutScores
    rank_reason: str


def _stage_score(text: str, profile: FounderProfile, matcher: Matcher) -> float:
    stage = profile.company.stage
    stage_keywords = profile.signals.stage_keywords.get(stage, [])
    base = keyword_score(text, stage_keywords, matcher=matcher)
    location = keyword_score(text, profile.signals.location_keywords, matcher=matcher)
    return min(100.0, base + min(20.0, location * 0.2))


def _deadline_score(deadline_at: date | None, today: date | None = None) -> float:
    if deadline_at is None:
        return 10.0
    today = today or date.today()
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
    today: date | None = None,
    matcher: Matcher = keyword_hits,
    actionability: bool = True,
) -> RankedOpportunity:
    """Score an opportunity against the founder profile.

    Each signal is a 0–100 keyword score; the total is their weighted sum using
    ``profile.priorities``, then discounted when the title looks like a listicle,
    press release or past cycle (see ``lib.scout.actionability``). ``today``,
    ``matcher`` and ``actionability`` are injectable so tests and the evaluation
    harness get deterministic, comparable results.
    """
    text = " ".join(filter(None, [title, snippet, description or "", stage or ""]))
    signals = profile.signals
    priorities = profile.priorities

    def kw(keywords: list[str]) -> float:
        return keyword_score(text, keywords, matcher=matcher)

    scores = ScoutScores(
        stage_fit=_stage_score(text, profile, matcher),
        ai_focus=kw(signals.ai_keywords),
        education_focus=kw(signals.education_keywords),
        language_preservation=kw(signals.language_preservation_keywords),
        minority_founder=kw(signals.minority_founder_keywords),
        deadline=_deadline_score(deadline_at, today),
    )

    total = (
        scores.stage_fit * priorities.stage_fit
        + scores.ai_focus * priorities.ai_focus
        + scores.education_focus * priorities.education_focus
        + scores.language_preservation * priorities.language_preservation
        + scores.minority_founder * priorities.minority_founder
        + scores.deadline * priorities.deadlines
    )
    reason = _build_reason(scores, category)
    if actionability:
        assessment = assess_title(title, today)
        total *= assessment.multiplier
        if assessment.flags:
            reason += f" · discounted: {', '.join(assessment.flags)}"
    scores.total = round(total, 1)

    return RankedOpportunity(scores=scores, rank_reason=reason)


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

# Full names plus the abbreviations search snippets actually use ("Sep",
# "Sept.", "Jun"). Longest-first so "sept" wins over "sep" and "june" over "jun".
_MONTH_TOKENS: dict[str, int] = {name: i + 1 for i, name in enumerate(_MONTH_NAMES)}
_MONTH_TOKENS.update({name[:3]: i + 1 for i, name in enumerate(_MONTH_NAMES)})
_MONTH_TOKENS["sept"] = 9
_MONTH_ALT = "|".join(sorted(_MONTH_TOKENS, key=len, reverse=True))

_ORDINAL = r"(?:st|nd|rd|th)?"
_ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
# "March 4, 2026" / "Sep 8th, 2026" / "Sept. 30" (year optional)
_MONTH_FIRST_RE = re.compile(
    rf"\b({_MONTH_ALT})\.?\s+(\d{{1,2}}){_ORDINAL}\b(?:,?\s+(20\d{{2}})\b)?"
)
# "25 June 2026" / "1st of March" (year optional)
_DAY_FIRST_RE = re.compile(
    rf"\b(\d{{1,2}}){_ORDINAL}\s+(?:of\s+)?({_MONTH_ALT})\b\.?(?:,?\s+(20\d{{2}})\b)?"
)
# "06/24/2026" — US order, falling back to DD/MM when the first part can't be a month.
_NUMERIC_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")

# Phrases that indicate a nearby date is actually an application deadline,
# as opposed to a publish date, an image caption, or an unrelated event date
# picked up from a noisy search snippet.
DEADLINE_KEYWORDS = (
    "deadline",
    "apply by",
    "apply before",
    "apply until",
    "applications close",
    "applications due",
    "applications are due",
    "application closes",
    "application deadline",
    "submissions close",
    "due by",
    "due on",
    "due date",
    "is due",
    "are due",
    "submission deadline",
    "submit by",
    "submit before",
    "closes",
    "close on",
    "closing on",
    "closing date",
    "must apply by",
    "no later than",
    "open through",
    "open until",
)

_PROXIMITY_WINDOW = 80
# Deadlines are almost always written after their keyword ("Deadline: June 30",
# "apply by Nov 1"); a date just *before* one is usually something else
# ("Applications open: June 1 / Deadline: June 30").
_PRECEDING_DATE_PENALTY = 40
# A date whose year had to be guessed is weaker evidence than one that states it.
_INFERRED_YEAR_PENALTY = 30


def _infer_year(month: int, day: int, text: str, today: date) -> date | None:
    """Pick a year for a date written without one ("Applications close November 1").

    Only consider years the snippet itself mentions (capped at next year so a
    "2030 vision" doesn't count) — that keeps a stale 2024 article's deadline in
    2024, where it correctly shows as expired. With no year in the text at all,
    consider last/this/next year. Either way, take the occurrence closest to today.
    """
    years = {int(y) for y in _YEAR_RE.findall(text) if int(y) <= today.year + 1}
    candidate_years = years or {today.year - 1, today.year, today.year + 1}
    options: list[date] = []
    for year in candidate_years:
        try:
            options.append(date(year, month, day))
        except ValueError:
            continue
    if not options:
        return None
    return min(options, key=lambda d: abs((d - today).days))


def _date_candidates(text: str, today: date) -> list[tuple[int, int, date, bool]]:
    """All (start, end, date, year_inferred) matches for the supported date formats.

    `text` must already have markdown emphasis stripped (see parse_deadline_from_text).
    """
    normalized = text.lower()
    candidates: list[tuple[int, int, date, bool]] = []

    def add(start: int, end: int, year: str | None, month: int, day: int) -> None:
        try:
            parsed = date(int(year), month, day) if year else _infer_year(month, day, text, today)
        except ValueError:
            return
        if parsed is not None:
            candidates.append((start, end, parsed, year is None))

    for m in _ISO_DATE_RE.finditer(normalized):
        add(m.start(), m.end(), m.group(1), int(m.group(2)), int(m.group(3)))
    for m in _MONTH_FIRST_RE.finditer(normalized):
        add(m.start(), m.end(), m.group(3), _MONTH_TOKENS[m.group(1)], int(m.group(2)))
    for m in _DAY_FIRST_RE.finditer(normalized):
        add(m.start(), m.end(), m.group(3), _MONTH_TOKENS[m.group(2)], int(m.group(1)))
    for m in _NUMERIC_DATE_RE.finditer(normalized):
        first, second = int(m.group(1)), int(m.group(2))
        month, day = (first, second) if first <= 12 else (second, first)
        add(m.start(), m.end(), m.group(3), month, day)
    return candidates


def _keyword_distance(date_start: int, date_end: int, kw_start: int, kw_end: int) -> int | None:
    """Effective distance from a keyword to a date, or None if out of range."""
    if kw_end <= date_start:
        gap = date_start - kw_end
        return gap if gap <= _PROXIMITY_WINDOW else None
    if date_end <= kw_start:
        gap = kw_start - date_end
        return gap + _PRECEDING_DATE_PENALTY if gap <= _PROXIMITY_WINDOW else None
    return 0


def parse_deadline_from_text(text: str, today: date | None = None) -> date | None:
    """Extract a deadline date — but only one that appears near deadline-indicating
    language (e.g. "deadline", "apply by", "closes on").

    A date found anywhere else in a search snippet (an image caption, a publish
    date, an unrelated event mentioned in the same page) is not trustworthy
    enough to store as the application deadline, so it's treated as unknown
    rather than guessed. Relative phrases ("closes in 30 days") are likewise
    ignored: they're relative to an unknown publish date, and anchoring them to
    today would push the deadline forward on every rescan.
    """
    # Scraped snippets carry markdown emphasis that can split a date apart
    # ("December 12, 202*****5**"), which would otherwise lose the year.
    text = text.replace("*", "")
    normalized = text.lower()

    keyword_spans = [
        (m.start(), m.end())
        for kw in DEADLINE_KEYWORDS
        for m in re.finditer(r"\b" + re.escape(kw) + r"s?\b", normalized)
    ]
    if not keyword_spans:
        return None

    today = today or date.today()
    near: list[tuple[int, date]] = []
    for start, end, parsed, year_inferred in _date_candidates(text, today):
        distances = [
            d
            for kw_start, kw_end in keyword_spans
            if (d := _keyword_distance(start, end, kw_start, kw_end)) is not None
        ]
        if distances:
            near.append((min(distances) + (_INFERRED_YEAR_PENALTY if year_inferred else 0), parsed))
    if not near:
        return None
    # Closest to deadline language wins. On an exact tie, prefer the next
    # upcoming date. Upcoming-ness is deliberately only a tiebreak: once a
    # program's real deadline has passed, jumping to some other future date on
    # the page (the program's end date, a demo day) would make it look open
    # when it isn't.
    return min(near, key=lambda c: (c[0], c[1] < today, c[1]))[1]
