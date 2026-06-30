from lib.agents.base import BaseAgent
from lib.schemas import AgentResult, SearchResult


class SocialAgent(BaseAgent):
    name = "social"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=0,
            message="Social agent stub — extend for content ideas and mentions",
        )
