from datetime import datetime
from pathlib import Path

from lib.agents.base import BaseAgent
from lib.db import upsert_by_url
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
        ranked_rows: list[tuple[float, dict]] = []

        for result in results:
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
            row = {
                "name": result.title[:200],
                "category": category,
                "organization": None,
                "amount": None,
                "stage": profile.company.stage,
                "description": snippet[:500] if snippet else None,
                "url": result.url,
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
                "raw_json": result.raw,
            }
            upsert_by_url(self.conn, "scout_opportunities", row)
            upserted += 1
            ranked_rows.append((ranked.scores.total, row))

        digest_path = self._write_digest(ranked_rows)
        top_score = ranked_rows[0][0] if ranked_rows else 0

        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=upserted,
            message=f"Scout complete — top score {top_score:.1f}. Digest: {digest_path.name}",
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
