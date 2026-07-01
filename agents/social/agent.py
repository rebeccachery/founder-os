from datetime import datetime

from lib.agents.base import BaseAgent
from lib.db import log_agent_run
from lib.schemas import AgentResult, SearchResult
from lib.social.context import collect_social_context
from lib.social.digest import write_content_digest, write_context_digest
from lib.social.generator import generate_social_content
from lib.social.storage import save_generation_drafts


class SocialAgent(BaseAgent):
    name = "social"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=0,
            message="Use run() for context collection and content generation",
        )

    def run(self) -> AgentResult:
        started_at = datetime.utcnow()
        try:
            context = collect_social_context(self.conn)
            context_md, _context_json = write_context_digest(context)
            generation = generate_social_content(context)
            content_md, _content_json = write_content_digest(context, generation)
            saved = save_generation_drafts(self.conn, generation)

            signal_count = (
                len(context.commits)
                + len(context.releases)
                + len(context.milestones)
                + len(context.features)
                + len(context.datasets)
            )
            generator_label = generation.llm_model if generation.llm_used else "templates"

            message = (
                f"Collected {signal_count} signals, saved {saved} drafts to DB "
                f"({generator_label}). "
                f"Context: {context_md.name}, Content: {content_md.name}"
            )

            result = AgentResult(
                agent_name=self.name,
                items_found=signal_count,
                items_upserted=saved,
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
