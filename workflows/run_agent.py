#!/usr/bin/env python3
"""CLI entrypoint for running Founder OS agents locally or in CI."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from lib.db import get_connection, init_db  # noqa: E402

AGENT_MODULES = {
    "funding_scout": ("agents.funding_scout.agent", "FundingScoutAgent"),
    "funding": ("agents.funding.agent", "FundingAgent"),
    "investors": ("agents.investors.agent", "InvestorsAgent"),
    "grants": ("agents.grants.agent", "GrantsAgent"),
    "crm": ("agents.crm.agent", "CrmAgent"),
    "social": ("agents.social.agent", "SocialAgent"),
    "research": ("agents.research.agent", "ResearchAgent"),
    "opportunities": ("agents.opportunities.agent", "OpportunitiesAgent"),
}

DAILY_AGENTS = ["funding_scout", "grants", "opportunities", "funding"]
WEEKLY_AGENTS = ["investors", "research"]


def load_agent(name: str):
    if name not in AGENT_MODULES:
        raise ValueError(f"Unknown agent: {name}. Choose from: {', '.join(AGENT_MODULES)}")
    module_path, class_name = AGENT_MODULES[name]
    module = importlib.import_module(module_path)
    agent_cls = getattr(module, class_name)
    agent_dir = ROOT / "agents" / name
    return agent_cls, agent_dir


def run_agent(name: str) -> None:
    agent_cls, agent_dir = load_agent(name)
    with get_connection() as conn:
        agent = agent_cls(conn, agent_dir)
        result = agent.run()
    print(f"[{name}] {result.status}: found={result.items_found}, upserted={result.items_upserted}")
    if result.message:
        print(f"  → {result.message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Founder OS agents")
    parser.add_argument("--agent", help="Run a single agent by name")
    parser.add_argument("--all", action="store_true", help="Run all agents")
    parser.add_argument("--daily", action="store_true", help="Run daily scan agents")
    parser.add_argument("--weekly", action="store_true", help="Run weekly scan agents")
    parser.add_argument("--init-db", action="store_true", help="Initialize database only")
    args = parser.parse_args()

    init_db()

    if args.init_db:
        print("Database initialized.")
        return

    if args.all:
        for name in AGENT_MODULES:
            run_agent(name)
        return

    if args.daily:
        for name in DAILY_AGENTS:
            run_agent(name)
        return

    if args.weekly:
        for name in WEEKLY_AGENTS:
            run_agent(name)
        return

    if args.agent:
        run_agent(args.agent)
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
