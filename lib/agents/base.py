from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import sqlite3

from lib.db import log_agent_run
from lib.paths import private_agent_queries_path
from lib.schemas import AgentResult, SearchResult
from lib.scout.queries import load_categorized_queries
from lib.search.client import load_queries, search


class BaseAgent(ABC):
    name: str = "base"
    queries_file: str = "queries.yaml"

    def __init__(self, conn: sqlite3.Connection, agent_dir: Path):
        self.conn = conn
        self.agent_dir = agent_dir

    def get_queries(self) -> list[str]:
        return load_queries(
            self.agent_dir / self.queries_file,
            merge_path=private_agent_queries_path(self.agent_dir),
        )

    def run_searches(self, max_results: int = 5) -> list[SearchResult]:
        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()
        for query in self.get_queries():
            for result in search(query, max_results=max_results):
                if result.url and result.url not in seen_urls:
                    seen_urls.add(result.url)
                    all_results.append(result)
        return all_results

    def run_categorized_searches(self, max_results: int = 5) -> list[SearchResult]:
        categorized = load_categorized_queries(
            self.agent_dir / self.queries_file,
            merge_path=private_agent_queries_path(self.agent_dir),
        )
        if not categorized:
            return self.run_searches(max_results=max_results)

        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()
        for category, queries in categorized.items():
            for query in queries:
                for result in search(query, max_results=max_results):
                    if result.url and result.url not in seen_urls:
                        seen_urls.add(result.url)
                        all_results.append(result.model_copy(update={"category": category}))
        return all_results

    @abstractmethod
    def process_results(self, results: list[SearchResult]) -> AgentResult:
        ...

    def run(self) -> AgentResult:
        started_at = datetime.utcnow()
        try:
            results = self.run_searches()
            agent_result = self.process_results(results)
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
