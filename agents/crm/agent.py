from lib.agents.base import BaseAgent
from lib.schemas import AgentResult, SearchResult


class CrmAgent(BaseAgent):
    name = "crm"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        # CRM agent is primarily manual; search results are logged but not auto-imported in v1.
        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=0,
            message="CRM agent stub — add contacts manually or extend this agent",
        )
