from pathlib import Path

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROFILE_PATH = ROOT / "config" / "oss_profile.yaml"

EVERGREEN_RESOURCE_TYPES = frozenset({"benchmark", "eval_tool"})


class OssPriorityWeights(BaseModel):
    task_fit: float = 0.30
    language_fit: float = 0.30
    recency: float = 0.20
    popularity: float = 0.10
    license_fit: float = 0.10


class OssSignalKeywords(BaseModel):
    task_keywords: list[str] = Field(default_factory=list)
    language_keywords: list[str] = Field(default_factory=list)
    target_language_codes: list[str] = Field(default_factory=list)
    target_language_names: list[str] = Field(default_factory=list)
    license_preferred: list[str] = Field(default_factory=list)


class RecencyRules(BaseModel):
    digest_recent_days: int = 90
    hard_filter_days: dict[str, int] = Field(
        default_factory=lambda: {"repo": 365, "model": 365}
    )


class OssProfile(BaseModel):
    priorities: OssPriorityWeights = Field(default_factory=OssPriorityWeights)
    signals: OssSignalKeywords = Field(default_factory=OssSignalKeywords)
    recency: RecencyRules = Field(default_factory=RecencyRules)


def load_oss_profile(path: Path | None = None) -> OssProfile:
    profile_path = path or DEFAULT_PROFILE_PATH
    if not profile_path.exists():
        return OssProfile()
    with profile_path.open() as f:
        data = yaml.safe_load(f) or {}
    return OssProfile.model_validate(data)
