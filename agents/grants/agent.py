from lib.agents.base import BaseAgent
from lib.db import upsert_by_url
from lib.schemas import AgentResult, SearchResult


class GrantsAgent(BaseAgent):
    name = "grants"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        upserted = 0
        for result in results:
            upsert_by_url(
                self.conn,
                "grants",
                {
                    "name": result.title[:200],
                    "funder": None,
                    "amount": None,
                    "eligibility": result.snippet[:500] if result.snippet else None,
                    "url": result.url,
                    "deadline_at": None,
                    "status": "new",
                    "source": result.source,
                    "raw_json": result.raw,
                },
            )
            upserted += 1
        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=upserted,
            message="Grants scan complete",
        )
