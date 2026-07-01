import json
import os
from datetime import datetime
from pathlib import Path

from lib.agents.base import BaseAgent
from lib.db import log_agent_run, upsert_by_url
from lib.discovery.clients.github import search_github_repos
from lib.discovery.clients.huggingface import search_hf_datasets, search_hf_models
from lib.discovery.clients.web import search_web
from lib.discovery.normalize import DiscoveryHit, dedupe_hits
from lib.discovery.profile import EVERGREEN_RESOURCE_TYPES, load_oss_profile
from lib.discovery.ranker import rank_oss_resource
from lib.discovery.recency import is_recent, should_ingest
from lib.paths import private_agent_queries_path
from lib.schemas import AgentResult
from lib.scout.queries import load_categorized_queries

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "reports"

CATEGORY_HANDLERS = {
    "datasets": "huggingface_datasets",
    "models": "huggingface_models",
    "repos": "github",
    "eval_tools": "github",
    "benchmarks": "web",
}


class OssDiscoveryAgent(BaseAgent):
    name = "oss_discovery"
    queries_file = "queries.yaml"

    def _max_results(self) -> int:
        return int(os.getenv("OSS_DISCOVERY_MAX_PER_QUERY", "10"))

    def discover(self) -> list[DiscoveryHit]:
        categorized = load_categorized_queries(
            self.agent_dir / self.queries_file,
            merge_path=private_agent_queries_path(self.agent_dir),
        )
        max_results = self._max_results()
        all_hits: list[DiscoveryHit] = []

        for category, queries in categorized.items():
            handler = CATEGORY_HANDLERS.get(category, "web")
            for query in queries:
                if handler == "huggingface_datasets":
                    hits = search_hf_datasets(query, max_results=max_results)
                elif handler == "huggingface_models":
                    hits = search_hf_models(query, max_results=max_results)
                elif handler == "github":
                    resource_type = "eval_tool" if category == "eval_tools" else "repo"
                    hits = search_github_repos(query, resource_type=resource_type, max_results=max_results)
                else:
                    hits = search_web(query, resource_type="benchmark", max_results=max_results)
                all_hits.extend(hits)

        return dedupe_hits(all_hits)

    def process_results(self, hits: list[DiscoveryHit]) -> AgentResult:
        profile = load_oss_profile()
        upserted = 0
        skipped_stale = 0
        ranked_rows: list[tuple[float, dict]] = []

        for hit in hits:
            if not should_ingest(hit, profile):
                skipped_stale += 1
                continue

            ranked = rank_oss_resource(hit, profile)
            row = {
                "name": hit.name[:200],
                "resource_type": hit.resource_type,
                "url": hit.url,
                "description": hit.description[:500] if hit.description else None,
                "organization": hit.organization,
                "license": hit.license,
                "stars": hit.stars,
                "task_tags": json.dumps(hit.task_tags) if hit.task_tags else None,
                "language_tags": json.dumps(hit.language_tags) if hit.language_tags else None,
                "metrics_json": json.dumps(hit.metrics_json) if hit.metrics_json else None,
                "published_at": hit.published_at,
                "last_updated_at": hit.last_updated_at,
                "status": "new",
                "source": hit.source,
                "score_total": ranked.scores.total,
                "score_task_fit": ranked.scores.task_fit,
                "score_language_fit": ranked.scores.language_fit,
                "score_recency": ranked.scores.recency,
                "score_popularity": ranked.scores.popularity,
                "rank_reason": ranked.rank_reason,
                "raw_json": hit.raw,
            }
            upsert_by_url(self.conn, "oss_resources", row)
            upserted += 1
            ranked_rows.append((ranked.scores.total, row))

        digest_path = self._write_digest(ranked_rows, profile)
        top_score = ranked_rows[0][0] if ranked_rows else 0
        skip_note = f", skipped {skipped_stale} stale repos/models" if skipped_stale else ""

        return AgentResult(
            agent_name=self.name,
            items_found=len(hits),
            items_upserted=upserted,
            message=(
                f"OSS discovery complete — top score {top_score:.1f}{skip_note}. "
                f"Digest: {digest_path.name}"
            ),
        )

    def run(self) -> AgentResult:
        started_at = datetime.utcnow()
        try:
            hits = self.discover()
            agent_result = self.process_results(hits)
            log_agent_run(
                self.conn,
                agent_name=self.name,
                started_at=started_at,
                status=agent_result.status,
                items_found=agent_result.items_found,
                items_upserted=agent_result.items_upserted,
                message=agent_result.message,
            )
            return agent_result
        except Exception as exc:
            log_agent_run(
                self.conn,
                agent_name=self.name,
                started_at=started_at,
                status="error",
                message=str(exc),
            )
            raise

    def _write_digest(self, ranked_rows: list[tuple[float, dict]], profile) -> Path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        digest_path = REPORTS_DIR / f"oss_{today}.md"
        recent_days = profile.recency.digest_recent_days

        ranked_rows.sort(key=lambda item: item[0], reverse=True)
        recent_rows = [
            row for score, row in ranked_rows
            if is_recent(row.get("last_updated_at"), recent_days)
        ]
        recent_urls = {row["url"] for row in recent_rows}
        evergreen_rows = [
            (score, row)
            for score, row in ranked_rows
            if row["resource_type"] in EVERGREEN_RESOURCE_TYPES and row["url"] not in recent_urls
        ]

        lines = [f"# OSS Discovery — {today}\n\n"]
        lines.append("Focus: **Haitian Creole** · speech · translation · pronunciation\n\n")

        by_type: dict[str, int] = {}
        for _, row in ranked_rows:
            by_type[row["resource_type"]] = by_type.get(row["resource_type"], 0) + 1
        if by_type:
            summary = ", ".join(
                f"{count} {rtype}{'s' if count != 1 else ''}"
                for rtype, count in sorted(by_type.items())
            )
            lines.append(f"Stored **{len(ranked_rows)}** resources ({summary})\n\n")

        lines.append(f"## Recent (updated in last {recent_days} days)\n\n")
        if recent_rows:
            for i, row in enumerate(recent_rows[:20], 1):
                lines.extend(self._format_digest_entry(i, row["score_total"], row))
        else:
            lines.append("_No resources updated in this window._\n\n")

        if evergreen_rows:
            lines.append("## Reference benchmarks & eval tools\n\n")
            lines.append("_Evergreen resources — included regardless of last update date._\n\n")
            for i, (score, row) in enumerate(evergreen_rows[:10], 1):
                lines.extend(self._format_digest_entry(i, score, row))

        digest_path.write_text("".join(lines))
        return digest_path

    def _format_digest_entry(self, index: int, score: float, row: dict) -> list[str]:
        lines = [f"### {index}. {row['name']} ({score:.1f})\n"]
        lines.append(f"- Type: {row['resource_type'].replace('_', ' ')}\n")
        lines.append(f"- Source: {row['source']}\n")
        lines.append(f"- URL: {row['url']}\n")
        if row.get("last_updated_at"):
            lines.append(f"- Updated: {row['last_updated_at']}\n")
        if row.get("organization"):
            lines.append(f"- Organization: {row['organization']}\n")
        if row.get("license"):
            lines.append(f"- License: {row['license']}\n")
        if row.get("stars"):
            lines.append(f"- Stars/downloads: {row['stars']}\n")
        if row.get("rank_reason"):
            lines.append(f"- Why: {row['rank_reason']}\n")
        if row.get("description"):
            lines.append(f"- {row['description']}\n")
        lines.append("\n")
        return lines
