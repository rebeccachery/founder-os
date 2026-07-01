from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from lib.paths import ROOT, resolve_config

SOCIAL_PROFILE_FILENAME = "social_profile.yaml"
FEATURES_FILENAME = "features.yaml"

REPO_PATH_ENV_VARS: dict[str, str] = {}


def repo_path_env_var(repo_name: str) -> str:
    return f"{repo_name.upper().replace('-', '_')}_PATH"


class ProductRepoConfig(BaseModel):
    owner: str = "your-github-username"
    name: str
    role: str = "showcase"
    weight: float = 1.0
    local_path: str = ""
    private: bool = False
    commit_detail: str = "subject_and_body"
    content_angle: str = ""
    fetch_commits: bool = True
    fetch_releases: bool = True
    fetch_milestones: bool = False


class GitHubConfig(BaseModel):
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
    company_name: str = "Your Company"
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
    repos: list[ProductRepoConfig] = Field(default_factory=list)
    exclude_repos: list[str] = Field(default_factory=list)
    since_days: int = 7
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
    repo: str | None = None


class ManualMilestone(BaseModel):
    name: str
    status: str
    target_date: date | str | None = None
    description: str | None = None
    repo: str | None = None


class FeaturesConfig(BaseModel):
    features: list[FeatureSignalConfig] = Field(default_factory=list)
    milestones: list[ManualMilestone] = Field(default_factory=list)


def resolve_repo_local_path(repo: ProductRepoConfig) -> Path:
    env_var = REPO_PATH_ENV_VARS.get(repo.name) or repo_path_env_var(repo.name)
    if env_var:
        import os

        override = os.getenv(env_var)
        if override:
            return Path(override).expanduser()

    if repo.local_path:
        path = Path(repo.local_path)
        if not path.is_absolute():
            path = ROOT / path
        return path

    return ROOT.parent / repo.name


def primary_repo(profile: SocialProfile) -> ProductRepoConfig | None:
    for repo in profile.repos:
        if repo.role == "primary":
            return repo
    return profile.repos[0] if profile.repos else None


def _normalize_profile_data(data: dict) -> dict:
    if data.get("repo") and not data.get("repos"):
        legacy = data.pop("repo")
        data["repos"] = [
            {
                "owner": legacy.get("owner", ""),
                "name": legacy.get("name", ""),
                "local_path": legacy.get("local_path", "."),
                "role": "primary",
            }
        ]
    return data


def load_social_profile(path: Path | None = None) -> SocialProfile:
    profile_path = path or resolve_config(SOCIAL_PROFILE_FILENAME)
    if profile_path is None:
        return SocialProfile()
    with profile_path.open() as f:
        data = yaml.safe_load(f) or {}
    data = _normalize_profile_data(data)
    return SocialProfile.model_validate(data)


def load_features_config(path: Path | None = None) -> FeaturesConfig:
    features_path = path or resolve_config(FEATURES_FILENAME)
    if features_path is None:
        return FeaturesConfig()
    with features_path.open() as f:
        data = yaml.safe_load(f) or {}
    return FeaturesConfig.model_validate(data)
