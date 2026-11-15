import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Visibility = Literal["private", "unlisted", "public"]
MemberRole = Literal["editor", "contributor", "viewer"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    logline: str = Field(default="", max_length=500)
    genre: str = Field(default="", max_length=80)
    visibility: Visibility = "private"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return value.strip()


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    logline: str | None = Field(default=None, max_length=500)
    genre: str | None = Field(default=None, max_length=80)
    visibility: Visibility | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str
    logline: str
    genre: str
    visibility: str
    current_phase: str
    owner_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    member_count: int = 0


class MemberRead(BaseModel):
    id: uuid.UUID
    display_name: str | None = None
    email: str | None = None
    invited_email: str | None = None
    role: str
    status: str
    created_at: datetime


class ProjectDetail(ProjectRead):
    members: list[MemberRead]


class InvitationCreate(BaseModel):
    email: EmailStr
    role: MemberRole = "contributor"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return str(value).strip().lower()


class ContributionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=30000)

    @field_validator("title", "body")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()


class ContributionRevisionCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=30000)

    @field_validator("title", "body")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ContributionRevisionRead(BaseModel):
    id: uuid.UUID
    revision_number: int
    title: str
    body: str
    author_user_id: uuid.UUID
    author_display_name: str
    created_at: datetime


class ContributionRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    author_user_id: uuid.UUID
    author_display_name: str
    title: str
    status: str
    current_revision_number: int
    current_revision_id: uuid.UUID
    current_body: str
    created_at: datetime
    updated_at: datetime


class ContributionDetail(ContributionRead):
    revisions: list[ContributionRevisionRead]


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    revision_id: uuid.UUID | None = None
    parent_comment_id: uuid.UUID | None = None

    @field_validator("body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        return value.strip()


class CommentRead(BaseModel):
    id: uuid.UUID
    contribution_id: uuid.UUID
    revision_id: uuid.UUID | None
    parent_comment_id: uuid.UUID | None
    author_user_id: uuid.UUID
    author_display_name: str
    body: str
    created_at: datetime


class SuggestionCreate(BaseModel):
    target_revision_id: uuid.UUID
    title: str = Field(min_length=1, max_length=160)
    rationale: str = Field(default="", max_length=10000)
    proposed_text: str = Field(min_length=1, max_length=30000)

    @field_validator("title", "rationale", "proposed_text")
    @classmethod
    def trim_fields(cls, value: str) -> str:
        return value.strip()


class SuggestionDecisionCreate(BaseModel):
    status: Literal["accepted", "rejected", "deferred"]
    note: str = Field(default="", max_length=5000)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str) -> str:
        return value.strip()


class SuggestionDecisionRead(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_display_name: str
    previous_status: str | None
    new_status: str
    note: str
    created_at: datetime


class SuggestionRead(BaseModel):
    id: uuid.UUID
    contribution_id: uuid.UUID
    target_revision_id: uuid.UUID
    author_user_id: uuid.UUID
    author_display_name: str
    title: str
    rationale: str
    proposed_text: str
    status: str
    created_at: datetime
    updated_at: datetime
    decisions: list[SuggestionDecisionRead] = Field(default_factory=list)



class NarrativeDraftSourceSelection(BaseModel):
    revision_id: uuid.UUID
    accepted_suggestion_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)


class NarrativeDraftCompile(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    sources: list[NarrativeDraftSourceSelection] = Field(min_length=1, max_length=30)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class NarrativeDraftVersionCreate(BaseModel):
    base_version_id: uuid.UUID
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=100000)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        return value.strip()


class NarrativeDraftSourceRead(BaseModel):
    id: uuid.UUID
    source_order: int
    source_kind: str
    contribution_id: uuid.UUID
    contribution_revision_id: uuid.UUID
    suggestion_id: uuid.UUID | None
    source_title: str
    source_text_snapshot: str


class NarrativeDraftVersionRead(BaseModel):
    id: uuid.UUID
    version_number: int
    title: str
    content: str
    status: str
    origin: str
    provider_name: str | None
    model_name: str | None
    prompt_version: str | None
    author_user_id: uuid.UUID
    author_display_name: str
    parent_version_id: uuid.UUID | None
    created_at: datetime
    sources: list[NarrativeDraftSourceRead] = Field(default_factory=list)


class NarrativeDraftDetail(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    current_version_number: int
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    versions: list[NarrativeDraftVersionRead] = Field(default_factory=list)



ApprovalMode = Literal["owner_only", "majority"]
ApprovalChoice = Literal["approve", "reject"]
ApprovalOutcome = Literal["approved", "rejected"]


class ApprovalRuleUpdate(BaseModel):
    mode: ApprovalMode


class ApprovalRuleRead(BaseModel):
    mode: ApprovalMode
    configured: bool
    updated_by_user_id: uuid.UUID | None = None
    updated_at: datetime | None = None


class ApprovalVoteCreate(BaseModel):
    choice: ApprovalChoice
    note: str = Field(default="", max_length=3000)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return value.strip()


class ApprovalVoteRead(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    voter_user_id: uuid.UUID
    voter_display_name: str
    choice: ApprovalChoice
    note: str
    created_at: datetime
    is_latest: bool
    counts_toward_result: bool


class ApprovalDecisionRead(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_display_name: str
    outcome: ApprovalOutcome
    rule_mode: ApprovalMode
    eligible_voter_count: int
    approve_count: int
    reject_count: int
    required_votes: int
    note: str
    created_at: datetime


class ApprovalVersionStatusRead(BaseModel):
    version_id: uuid.UUID
    version_number: int
    is_current_version: bool
    rule_mode: ApprovalMode
    ballot_opened_at: datetime | None = None
    eligible_voter_count: int
    required_votes: int
    approve_count: int
    reject_count: int
    current_user_vote: ApprovalChoice | None = None
    can_vote: bool
    can_finalize: bool
    decision_outcome: ApprovalOutcome | None = None
    votes: list[ApprovalVoteRead] = Field(default_factory=list)
    decision: ApprovalDecisionRead | None = None


class PhaseTransitionRead(BaseModel):
    id: uuid.UUID
    from_phase: str
    to_phase: str
    actor_user_id: uuid.UUID
    actor_display_name: str
    narrative_version_id: uuid.UUID | None
    reason: str
    created_at: datetime


class ApprovalOverview(BaseModel):
    project_id: uuid.UUID
    current_phase: str
    rule: ApprovalRuleRead
    versions: list[ApprovalVersionStatusRead] = Field(default_factory=list)
    phase_history: list[PhaseTransitionRead] = Field(default_factory=list)


class ApprovalDecisionCreate(BaseModel):
    note: str = Field(default="", max_length=3000)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return value.strip()
