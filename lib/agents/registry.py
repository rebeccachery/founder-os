"""Single source of truth for which agents exist and when they run.

Both the CLI (``workflows/run_agent.py``) and the API (``api/routes/agents.py``)
resolve agents through here, so adding an agent is a one-line change.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from lib.agents.base import BaseAgent

ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = ROOT / "agents"

Schedule = Literal["daily", "weekly", "manual"]


@dataclass(frozen=True)
class AgentSpec:
    name: str
    target: str  # "module.path:ClassName"
    schedule: Schedule

    @property
    def directory(self) -> Path:
        return AGENTS_DIR / self.name

    def load(self) -> type[BaseAgent]:
        module_path, class_name = self.target.split(":")
        return getattr(importlib.import_module(module_path), class_name)


AGENTS: dict[str, AgentSpec] = {
    spec.name: spec
    for spec in (
        AgentSpec("funding_scout", "agents.funding_scout.agent:FundingScoutAgent", "daily"),
        AgentSpec(
            "executive_assistant",
            "agents.executive_assistant.agent:ExecutiveAssistantAgent",
            "daily",
        ),
        AgentSpec("investors", "agents.investors.agent:InvestorsAgent", "weekly"),
        AgentSpec("research", "agents.research.agent:ResearchAgent", "weekly"),
        AgentSpec("oss_discovery", "agents.oss_discovery.agent:OssDiscoveryAgent", "weekly"),
        AgentSpec("crm", "agents.crm.agent:CrmAgent", "manual"),
        AgentSpec("social", "agents.social.agent:SocialAgent", "manual"),
    )
}


def get_agent(name: str) -> AgentSpec:
    try:
        return AGENTS[name]
    except KeyError:
        raise ValueError(f"Unknown agent: {name}. Choose from: {', '.join(AGENTS)}") from None


def agents_for(schedule: Schedule) -> list[AgentSpec]:
    return [spec for spec in AGENTS.values() if spec.schedule == schedule]
