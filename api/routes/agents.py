from fastapi import APIRouter, Depends, HTTPException

from api.database import db_session
from api.deps import verify_api_key
from lib.agents.registry import AGENTS, AgentSpec
from lib.schemas import AgentResult

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _run(spec: AgentSpec) -> AgentResult:
    with db_session() as conn:
        return spec.load()(conn, spec.directory).run()


@router.get("")
def list_agents(_: None = Depends(verify_api_key)):
    return {
        "agents": list(AGENTS),
        "schedules": {name: spec.schedule for name, spec in AGENTS.items()},
    }


@router.post("/run/{agent_name}", response_model=AgentResult)
def run_agent(agent_name: str, _: None = Depends(verify_api_key)):
    spec = AGENTS.get(agent_name)
    if spec is None or not spec.directory.exists():
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")
    return _run(spec)


@router.post("/run-all")
def run_all_agents(_: None = Depends(verify_api_key)):
    return {"results": [_run(spec) for spec in AGENTS.values()]}
