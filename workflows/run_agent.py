#!/usr/bin/env python3
"""CLI entrypoint for running Founder OS agents locally or from the nightly job."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from lib.agents.registry import AGENTS, AgentSpec, agents_for, get_agent  # noqa: E402
from lib.db import get_connection, init_db  # noqa: E402
from lib.logging_setup import configure_logging  # noqa: E402

log = logging.getLogger("founder_os.run")


def run_agent(spec: AgentSpec) -> bool:
    """Run one agent. Returns False (instead of raising) so a batch keeps going."""
    started = time.perf_counter()
    try:
        with get_connection() as conn:
            result = spec.load()(conn, spec.directory).run()
    except Exception:
        log.exception("agent failed", extra={"agent": spec.name})
        return False
    log.info(
        "agent finished",
        extra={
            "agent": spec.name,
            "status": result.status,
            "found": result.items_found,
            "upserted": result.items_upserted,
            "seconds": round(time.perf_counter() - started, 1),
        },
    )
    if result.message:
        level = logging.ERROR if result.status == "error" else logging.INFO
        log.log(level, result.message, extra={"agent": spec.name})
    return result.status != "error"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Founder OS agents")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--agent", choices=sorted(AGENTS), help="Run a single agent by name")
    group.add_argument("--all", action="store_true", help="Run all agents")
    group.add_argument("--daily", action="store_true", help="Run daily agents")
    group.add_argument("--weekly", action="store_true", help="Run weekly agents")
    group.add_argument("--init-db", action="store_true", help="Initialize database only")
    args = parser.parse_args()

    configure_logging()
    init_db()

    if args.init_db:
        log.info("database initialized")
        return

    if args.agent:
        specs = [get_agent(args.agent)]
    elif args.all:
        specs = list(AGENTS.values())
    elif args.daily:
        specs = agents_for("daily")
    elif args.weekly:
        specs = agents_for("weekly")
    else:
        parser.print_help()
        sys.exit(1)

    failures = [spec.name for spec in specs if not run_agent(spec)]
    if failures:
        log.error("some agents failed", extra={"failed": ",".join(failures)})
        sys.exit(1)


if __name__ == "__main__":
    main()
