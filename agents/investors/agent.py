from lib.agents.base import BaseAgent
from lib.db import upsert_by_url
from lib.schemas import AgentResult, SearchResult


class InvestorsAgent(BaseAgent):
    name = "investors"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        upserted = 0
        for result in results:
            upsert_by_url(
                self.conn,
                "investors",
                {
                    "name": result.title[:200],
                    "firm": None,
                    "stage": None,
                    "thesis": result.snippet[:500] if result.snippet else None,
                    "url": result.url,
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
            message="Investors scan complete",
        )
