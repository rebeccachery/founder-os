from datetime import datetime

from lib.agents.base import BaseAgent
from lib.assistant.briefing import briefing_to_db_row, build_briefing
from lib.assistant.digest import write_briefing_digest
from lib.db import log_agent_run, upsert_briefing
from lib.schemas import AgentResult, SearchResult


class ExecutiveAssistantAgent(BaseAgent):
    name = "executive_assistant"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=0,
            message="Use run() for briefing generation",
        )

    def run(self) -> AgentResult:
        started_at = datetime.utcnow()
        try:
            briefing = build_briefing(self.conn)
            upsert_briefing(self.conn, briefing_to_db_row(briefing))
            digest_path = write_briefing_digest(briefing)

            item_count = (
                len(briefing.priorities)
                + len(briefing.follow_ups)
                + len(briefing.deadlines)
                + len(briefing.applications)
            )

            message = (
                f"Briefing for {briefing.briefing_date.isoformat()} — "
                f"{len(briefing.priorities)} priorities, "
                f"{len(briefing.conflicts)} conflicts, "
                f"{item_count} total items. "
                f"Digest: {digest_path.name}"
            )

            result = AgentResult(
                agent_name=self.name,
                items_found=item_count,
                items_upserted=1,
                message=message,
            )
            log_agent_run(
                self.conn,
                agent_name=self.name,
                started_at=started_at,
                status=result.status,
                items_found=result.items_found,
                items_upserted=result.items_upserted,
                message=result.message,
            )
            return result
        except Exception as exc:
            log_agent_run(
                self.conn,
                agent_name=self.name,
                started_at=started_at,
                status="error",
                message=str(exc),
            )
            raise
