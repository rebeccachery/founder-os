from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from api.database import db_session
from api.deps import verify_api_key
from lib.schemas import AgentResult

router = APIRouter(prefix="/api/agents", tags=["agents"])

ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = ROOT / "agents"

AGENT_MODULES = {
    "funding_scout": "agents.funding_scout.agent.FundingScoutAgent",
    "funding": "agents.funding.agent.FundingAgent",
    "investors": "agents.investors.agent.InvestorsAgent",
    "grants": "agents.grants.agent.GrantsAgent",
    "crm": "agents.crm.agent.CrmAgent",
    "social": "agents.social.agent.SocialAgent",
    "research": "agents.research.agent.ResearchAgent",
    "opportunities": "agents.opportunities.agent.OpportunitiesAgent",
}


def _load_agent_class(dotted: str):
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


@router.get("")
def list_agents(_: None = Depends(verify_api_key)):
    return {"agents": list(AGENT_MODULES.keys())}


@router.post("/run/{agent_name}", response_model=AgentResult)
def run_agent(agent_name: str, _: None = Depends(verify_api_key)):
    if agent_name not in AGENT_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    agent_dir = AGENTS_DIR / agent_name
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent directory not found: {agent_name}")

    agent_cls = _load_agent_class(AGENT_MODULES[agent_name])
    with db_session() as conn:
        agent = agent_cls(conn, agent_dir)
        return agent.run()


@router.post("/run-all")
def run_all_agents(_: None = Depends(verify_api_key)):
    results: list[AgentResult] = []
    for name in AGENT_MODULES:
        agent_dir = AGENTS_DIR / name
        agent_cls = _load_agent_class(AGENT_MODULES[name])
        with db_session() as conn:
            agent = agent_cls(conn, agent_dir)
            results.append(agent.run())
    return {"results": results}
