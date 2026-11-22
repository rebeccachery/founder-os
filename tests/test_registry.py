import pytest

from lib.agents.base import BaseAgent
from lib.agents.registry import AGENTS, agents_for, get_agent


@pytest.mark.parametrize("name", list(AGENTS))
def test_every_registered_agent_imports_and_has_a_directory(name):
    spec = AGENTS[name]
    assert issubclass(spec.load(), BaseAgent)
    assert spec.directory.is_dir()


def test_schedules():
    assert [s.name for s in agents_for("daily")] == ["funding_scout", "executive_assistant"]
    assert {s.name for s in agents_for("weekly")} == {"investors", "research", "oss_discovery"}


def test_unknown_agent():
    with pytest.raises(ValueError, match="Unknown agent"):
        get_agent("nope")
