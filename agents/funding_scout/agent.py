from datetime import datetime
from pathlib import Path

from lib.agents.base import BaseAgent
from lib.db import find_likely_duplicate_scout_opportunity, upsert_by_url
from lib.opportunities.intake import is_social_url, normalize_url
from lib.schemas import AgentResult, SearchResult
from lib.scout.profile import load_founder_profile
from lib.scout.ranker import parse_deadline_from_text, rank_opportunity

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "reports"


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

            category = result.category or "unknown"
            snippet = result.snippet or ""
            deadline_at = parse_deadline_from_text(f"{result.title} {snippet}")
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
            message += f" ({skipped} low-quality results skipped: social links / malformed URLs)"

        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=upserted,
            message=message,
        )

    def _write_digest(self, ranked_rows: list[tuple[float, dict]]) -> Path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        digest_path = REPORTS_DIR / f"scout_{today}.md"

        ranked_rows.sort(key=lambda item: item[0], reverse=True)
        lines = [f"# Funding Scout — {today}\n\n"]
        lines.append(f"Profile: **{load_founder_profile().company.stage}** · ")
        lines.append("EdTech · translation · pronunciation · underresourced languages · NYC\n\n")

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
