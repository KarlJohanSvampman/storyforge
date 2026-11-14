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
    decisions: list[SuggestionDecisionRead] = []
