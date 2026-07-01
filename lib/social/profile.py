from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SOCIAL_PROFILE_PATH = ROOT / "config" / "social_profile.yaml"
DEFAULT_FEATURES_PATH = ROOT / "config" / "features.yaml"


class RepoConfig(BaseModel):
    owner: str = ""
    name: str = ""
    local_path: str = "."
    since_days: int = 7


class GitHubConfig(BaseModel):
    fetch_commits: bool = True
    fetch_releases: bool = True
    fetch_milestones: bool = True
    prefer_local_git: bool = True


class DatasetConfig(BaseModel):
    resource_types: list[str] = Field(default_factory=lambda: ["dataset"])
    min_score: float = 5.0
    recent_days: int = 90
    limit: int = 10


class GenerationConfig(BaseModel):
    min_signal_score: float = 6.0
    max_signals: int = 5
    content_types: list[str] = Field(
        default_factory=lambda: [
            "twitter_thread",
            "linkedin_post",
            "demo_idea",
            "launch_announcement",
        ]
    )


class VoiceConfig(BaseModel):
    tone: str = "founder-led, technical but accessible"
    hashtags: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    cta_url: str = ""


class LlmConfig(BaseModel):
    provider: str = "ollama"
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434/v1"
    temperature: float = 0.7


class SocialProfile(BaseModel):
    repo: RepoConfig = Field(default_factory=RepoConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    datasets: DatasetConfig = Field(default_factory=DatasetConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)


class FeatureSignalConfig(BaseModel):
    name: str
    status: str
    hook: str | None = None
    shipped_at: date | str | None = None
    url: str | None = None


class ManualMilestone(BaseModel):
    name: str
    status: str
    target_date: date | str | None = None
    description: str | None = None


class FeaturesConfig(BaseModel):
    features: list[FeatureSignalConfig] = Field(default_factory=list)
    milestones: list[ManualMilestone] = Field(default_factory=list)


def load_social_profile(path: Path | None = None) -> SocialProfile:
    profile_path = path or DEFAULT_SOCIAL_PROFILE_PATH
    if not profile_path.exists():
        return SocialProfile()
    with profile_path.open() as f:
        data = yaml.safe_load(f) or {}
    return SocialProfile.model_validate(data)


def load_features_config(path: Path | None = None) -> FeaturesConfig:
    features_path = path or DEFAULT_FEATURES_PATH
    if not features_path.exists():
        return FeaturesConfig()
    with features_path.open() as f:
        data = yaml.safe_load(f) or {}
    return FeaturesConfig.model_validate(data)
