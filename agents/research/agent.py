from datetime import datetime
from pathlib import Path

from lib.agents.base import BaseAgent
from lib.schemas import AgentResult, SearchResult

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "reports"


class ResearchAgent(BaseAgent):
    name = "research"

    def process_results(self, results: list[SearchResult]) -> AgentResult:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        report_path = REPORTS_DIR / f"research_{today}.md"

        lines = [f"# Research Report — {today}\n"]
        for i, result in enumerate(results, 1):
            lines.append(f"## {i}. {result.title}\n")
            lines.append(f"- URL: {result.url}\n")
            if result.snippet:
                lines.append(f"- {result.snippet}\n")
            lines.append("\n")

        report_path.write_text("".join(lines))

        return AgentResult(
            agent_name=self.name,
            items_found=len(results),
            items_upserted=0,
            message=f"Report written to {report_path.name}",
        )
