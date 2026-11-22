from datetime import date
from pathlib import Path

from lib.agents.base import BaseAgent
from lib.db import find_likely_duplicate_scout_opportunity, upsert_by_url
from lib.opportunities.intake import is_social_url, normalize_url
from lib.schemas import AgentResult, SearchResult
from lib.scout.profile import load_founder_profile
from lib.scout.ranker import parse_deadline_from_text, rank_opportunity
from lib.timeutil import utcnow_naive

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "reports"

# Below this, a provider's own relevance score means the result is a generic
# reference page (a dictionary entry, a Wikipedia article, an unrelated org
# with a similar name) rather than an actual opportunity — calibrated against
# real results: e.g. Wikipedia's "Language" article and a same-named-but-
# unrelated "NSF" (National Sanitation Foundation, not National Science
# Foundation) both score well under this on topical relevance despite
# sometimes still matching our own keyword-based founder-fit scoring.
MIN_SOURCE_RELEVANCE = 0.15


class FundingScoutAgent(BaseAgent):
    name = "funding_scout"

    def run_searches(self, max_results: int = 5) -> list[SearchResult]:
        return self.run_categorized_searches(max_results=max_results)

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        profile = load_founder_profile()
        upserted = 0
        skipped = 0
        ranked_rows: list[tuple[float, dict]] = []

        for result in results:
            # Reject social-feed URLs (a post/reel is never an application page)
            # and anything that isn't a well-formed absolute URL (search
            # providers sometimes return internal redirect-wrapper artifacts).
            if not result.url:
                skipped += 1
                continue
            try:
                url = normalize_url(result.url)
            except ValueError:
                skipped += 1
                continue
            if is_social_url(url):
                skipped += 1
                continue
            if (
                result.source_relevance is not None
                and result.source_relevance < MIN_SOURCE_RELEVANCE
            ):
                skipped += 1
                continue

            category = result.category or "unknown"
            snippet = result.snippet or ""
            deadline_at = parse_deadline_from_text(f"{result.title} {snippet}")
            if deadline_at is None:
                # Providers return a different snippet for the same page from run
                # to run; one that happens to omit the date shouldn't erase a
                # deadline an earlier run already found.
                deadline_at = self._existing_deadline(url)
            ranked = rank_opportunity(
                title=result.title,
                snippet=snippet,
                category=category,
                deadline_at=deadline_at,
                profile=profile,
            )
            name = result.title[:200]

            raw_json = dict(result.raw)
            duplicate_of = find_likely_duplicate_scout_opportunity(
                self.conn, name=name, category=category, exclude_url=url
            )
            if duplicate_of is not None:
                raw_json["likely_duplicate_of"] = duplicate_of

            row = {
                "name": name,
                "category": category,
                "organization": None,
                "amount": None,
                "stage": profile.company.stage,
                "description": snippet[:500] if snippet else None,
                "url": url,
                "deadline_at": deadline_at.isoformat() if deadline_at else None,
                "status": "new",
                "source": result.source,
                "score_total": ranked.scores.total,
                "score_stage_fit": ranked.scores.stage_fit,
                "score_ai_focus": ranked.scores.ai_focus,
                "score_education": ranked.scores.education_focus,
                "score_language_preservation": ranked.scores.language_preservation,
                "score_minority_founder": ranked.scores.minority_founder,
                "score_deadline": ranked.scores.deadline,
                "rank_reason": ranked.rank_reason,
                "raw_json": raw_json,
            }
            upsert_by_url(self.conn, "scout_opportunities", row)
            upserted += 1
            ranked_rows.append((ranked.scores.total, row))

        digest_path = self._write_digest(ranked_rows)
        top_score = ranked_rows[0][0] if ranked_rows else 0

        message = f"Scout complete — top score {top_score:.1f}. Digest: {digest_path.name}"
        if skipped:
            message += (
                f" ({skipped} low-quality results skipped: social links / "
                "malformed URLs / low source relevance)"
            )

        if not results:
            # ~50 queries returning nothing is never a quiet day; it means every
            # provider is unconfigured or failing. Surface it so the nightly job
            # notifies instead of reporting a hollow success.
            return AgentResult(
                agent_name=self.name,
                items_found=0,
                items_upserted=0,
                status="error",
                message="No results from any search provider — check API keys and SEARCH_FALLBACK_ORDER.",
            )

        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=upserted,
            message=message,
        )

    def _existing_deadline(self, url: str) -> date | None:
        row = self.conn.execute(
            "SELECT deadline_at FROM scout_opportunities WHERE url = ?", (url,)
        ).fetchone()
        if row is None or not row["deadline_at"]:
            return None
        try:
            return date.fromisoformat(str(row["deadline_at"])[:10])
        except ValueError:
            return None

    def _write_digest(self, ranked_rows: list[tuple[float, dict]]) -> Path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        today = utcnow_naive().strftime("%Y-%m-%d")
        digest_path = REPORTS_DIR / f"scout_{today}.md"

        ranked_rows.sort(key=lambda item: item[0], reverse=True)
        lines = [f"# Funding Scout — {today}\n\n"]
        company = load_founder_profile().company
        focus = " · ".join(filter(None, [company.stage, *company.geography]))
        lines.append(f"Profile: **{company.name}** · {focus}\n\n")

        for i, (score, row) in enumerate(ranked_rows[:20], 1):
            lines.append(f"## {i}. {row['name']} ({score:.1f})\n")
            lines.append(f"- Category: {row['category'].replace('_', ' ')}\n")
            lines.append(f"- URL: {row['url']}\n")
            if row.get("deadline_at"):
                lines.append(f"- Deadline: {row['deadline_at']}\n")
            if row.get("rank_reason"):
                lines.append(f"- Why: {row['rank_reason']}\n")
            if row.get("description"):
                lines.append(f"- {row['description']}\n")
            lines.append("\n")

        digest_path.write_text("".join(lines))
        return digest_path
