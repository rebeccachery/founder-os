from pathlib import Path

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROFILE_PATH = ROOT / "config" / "founder_profile.yaml"


class CompanyProfile(BaseModel):
    name: str = "Startup"
    stage: str = "pre-seed"
    description: str = ""
    geography: list[str] = Field(default_factory=list)


class PriorityWeights(BaseModel):
    stage_fit: float = 0.25
    ai_focus: float = 0.20
    education_focus: float = 0.20
    language_preservation: float = 0.15
    minority_founder: float = 0.10
    deadlines: float = 0.10


class SignalKeywords(BaseModel):
    ai_keywords: list[str] = Field(default_factory=list)
    education_keywords: list[str] = Field(default_factory=list)
    language_preservation_keywords: list[str] = Field(default_factory=list)
    minority_founder_keywords: list[str] = Field(default_factory=list)
    stage_keywords: dict[str, list[str]] = Field(default_factory=dict)
    location_keywords: list[str] = Field(default_factory=list)


class FounderProfile(BaseModel):
    company: CompanyProfile = Field(default_factory=CompanyProfile)
    priorities: PriorityWeights = Field(default_factory=PriorityWeights)
    signals: SignalKeywords = Field(default_factory=SignalKeywords)


def load_founder_profile(path: Path | None = None) -> FounderProfile:
    profile_path = path or DEFAULT_PROFILE_PATH
    if not profile_path.exists():
        return FounderProfile()
    with profile_path.open() as f:
        data = yaml.safe_load(f) or {}
    return FounderProfile.model_validate(data)
