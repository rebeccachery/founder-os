from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ItemStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    APPLIED = "applied"
    PASSED = "passed"
    ARCHIVED = "archived"


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
    category: str = ""


class ScoutScores(BaseModel):
    total: float = 0.0
    stage_fit: float = 0.0
    ai_focus: float = 0.0
    education_focus: float = 0.0
    language_preservation: float = 0.0
    minority_founder: float = 0.0
    deadline: float = 0.0


class ScoutOpportunity(BaseModel):
    id: int | None = None
    name: str
    category: str
    organization: str | None = None
    amount: str | None = None
    stage: str | None = None
    description: str | None = None
    url: str | None = None
    deadline_at: date | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    score_total: float | None = None
    score_stage_fit: float | None = None
    score_ai_focus: float | None = None
    score_education: float | None = None
    score_language_preservation: float | None = None
    score_minority_founder: float | None = None
    score_deadline: float | None = None
    rank_reason: str | None = None
    raw_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentResult(BaseModel):
    agent_name: str
    items_found: int
    items_upserted: int
    status: str = "success"
    message: str = ""


class Investor(BaseModel):
    id: int | None = None
    name: str
    firm: str | None = None
    stage: str | None = None
    thesis: str | None = None
    url: str | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    raw_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FundingOpportunity(BaseModel):
    id: int | None = None
    name: str
    organization: str | None = None
    amount: str | None = None
    stage: str | None = None
    description: str | None = None
    url: str | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    raw_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Grant(BaseModel):
    id: int | None = None
    name: str
    funder: str | None = None
    amount: str | None = None
    eligibility: str | None = None
    url: str | None = None
    deadline_at: date | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    raw_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Competition(BaseModel):
    id: int | None = None
    name: str
    organizer: str | None = None
    prize: str | None = None
    url: str | None = None
    deadline_at: date | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    raw_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Deadline(BaseModel):
    id: int | None = None
    title: str
    deadline_at: date
    category: str
    source_id: int | None = None
    url: str | None = None
    is_estimated: bool = False
    status: ItemStatus = ItemStatus.NEW


class Contact(BaseModel):
    id: int | None = None
    name: str
    organization: str | None = None
    email: str | None = None
    role: str | None = None
    notes: str | None = None
    last_touch_at: date | None = None
    next_follow_up_at: date | None = None
    status: ItemStatus = ItemStatus.NEW
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OssScores(BaseModel):
    total: float = 0.0
    task_fit: float = 0.0
    language_fit: float = 0.0
    recency: float = 0.0
    popularity: float = 0.0
    license_fit: float = 0.0


class OssResource(BaseModel):
    id: int | None = None
    name: str
    resource_type: str
    url: str
    description: str | None = None
    organization: str | None = None
    license: str | None = None
    stars: int | None = None
    task_tags: list[str] = Field(default_factory=list)
    language_tags: list[str] = Field(default_factory=list)
    metrics_json: dict[str, Any] | None = None
    published_at: date | None = None
    last_updated_at: date | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    score_total: float | None = None
    score_task_fit: float | None = None
    score_language_fit: float | None = None
    score_recency: float | None = None
    score_popularity: float | None = None
    rank_reason: str | None = None
    raw_json: dict[str, Any] | None = None
    discovered_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Stats(BaseModel):
    investors: int
    funding: int
    grants: int
    competitions: int
    scout: int
    oss: int = 0
    social: int = 0
    deadlines_upcoming: int
    contacts: int
    new_items: int


class AgentRun(BaseModel):
    id: int | None = None
    agent_name: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    items_found: int = 0
    items_upserted: int = 0
    message: str | None = None


class CommitSignal(BaseModel):
    sha: str
    subject: str
    body: str | None = None
    author: str
    committed_at: datetime
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    url: str | None = None


class ReleaseSignal(BaseModel):
    tag: str
    name: str | None = None
    body: str | None = None
    published_at: datetime
    url: str | None = None
    prerelease: bool = False


class MilestoneSignal(BaseModel):
    title: str
    description: str | None = None
    state: str
    open_issues: int = 0
    closed_issues: int = 0
    due_on: date | None = None
    closed_at: datetime | None = None
    url: str | None = None
    source: str = "github"


class FeatureSignal(BaseModel):
    name: str
    status: str
    hook: str | None = None
    shipped_at: date | None = None
    url: str | None = None


class DatasetSignal(BaseModel):
    id: int | None = None
    name: str
    url: str
    description: str | None = None
    score_total: float | None = None
    rank_reason: str | None = None
    resource_type: str
    discovered_at: datetime | None = None


class SocialContext(BaseModel):
    period_start: datetime
    period_end: datetime
    commits: list[CommitSignal] = Field(default_factory=list)
    releases: list[ReleaseSignal] = Field(default_factory=list)
    milestones: list[MilestoneSignal] = Field(default_factory=list)
    features: list[FeatureSignal] = Field(default_factory=list)
    datasets: list[DatasetSignal] = Field(default_factory=list)
    company_name: str = ""
    company_stage: str = ""
    repo_owner: str = ""
    repo_name: str = ""


class BriefingItem(BaseModel):
    title: str
    category: str
    due_at: str | None = None
    priority_score: float = 0.0
    reason: str = ""
    url: str | None = None
    source_id: int | None = None
    status: str | None = None


class Conflict(BaseModel):
    summary: str
    items: list[BriefingItem] = Field(default_factory=list)
    severity: str = "medium"


class ExecutiveBriefing(BaseModel):
    briefing_date: date
    generated_at: datetime
    priorities: list[BriefingItem] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    follow_ups: list[BriefingItem] = Field(default_factory=list)
    deadlines: list[BriefingItem] = Field(default_factory=list)
    meetings: list[BriefingItem] = Field(default_factory=list)
    applications: list[BriefingItem] = Field(default_factory=list)


class SavedOpportunityCreate(BaseModel):
    url: str | None = None
    name: str | None = None
    category: str | None = None
    deadline_at: date | None = None
    description: str | None = None
    source_tweet_url: str | None = None
    shared_by: str | None = None


class SavedOpportunity(BaseModel):
    id: int
    name: str
    category: str
    url: str | None = None
    deadline_at: date | None = None
    status: ItemStatus = ItemStatus.NEW
    source: str | None = None
    score_total: float | None = None
    rank_reason: str | None = None
    description: str | None = None
    created: bool = True


class RankedSignal(BaseModel):
    signal_type: str
    signal_key: str
    title: str
    summary: str
    score: float
    rank_reason: str
    source_ref: dict[str, Any] = Field(default_factory=dict)


class SocialDraft(BaseModel):
    content_type: str
    platform: str
    title: str
    hook: str
    body: str
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    signal_score: float | None = None


class SocialGenerationResult(BaseModel):
    ranked_signals: list[RankedSignal] = Field(default_factory=list)
    drafts: list[SocialDraft] = Field(default_factory=list)
    llm_used: bool = False
    llm_model: str | None = None


class SocialPostStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    SKIPPED = "skipped"
    ARCHIVED = "archived"


class SocialPost(BaseModel):
    id: int | None = None
    content_type: str
    platform: str | None = None
    title: str | None = None
    body: str
    hook: str | None = None
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    signal_score: float | None = None
    status: SocialPostStatus = SocialPostStatus.DRAFT
    llm_model: str | None = None
    generated_at: datetime | None = None
    posted_at: datetime | None = None
    raw_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
