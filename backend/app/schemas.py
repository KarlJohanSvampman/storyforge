import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Visibility = Literal["private", "unlisted", "public"]
ProjectFormat = Literal["movie", "tv_series"]
ProjectCategory = Literal["fiction", "documentary"]
MemberRole = Literal["editor", "contributor", "viewer"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    logline: str = Field(default="", max_length=500)
    genre: str = Field(default="", max_length=80)
    format: ProjectFormat = "movie"
    category: ProjectCategory = "fiction"
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
    format: ProjectFormat | None = None
    category: ProjectCategory | None = None
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
    format: ProjectFormat
    category: ProjectCategory
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


# M1.1 storyboard and creative asset contracts
class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    visual_description: str = Field(default="", max_length=10000)
    personality_notes: str = Field(default="", max_length=10000)

    @field_validator("name", "description", "visual_description", "personality_notes")
    @classmethod
    def clean_character_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def require_character_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Character name cannot be blank.")
        return value.strip()


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    visual_description: str | None = Field(default=None, max_length=10000)
    personality_notes: str | None = Field(default=None, max_length=10000)
    status: Literal["active", "archived"] | None = None

    @field_validator("name", "description", "visual_description", "personality_notes")
    @classmethod
    def clean_character_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("name")
    @classmethod
    def require_character_name_when_set(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Character name cannot be blank.")
        return value.strip() if value is not None else None


class CharacterRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str
    visual_description: str
    personality_notes: str
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    environment_type: str = Field(default="unspecified", max_length=40)
    time_period: str = Field(default="", max_length=120)
    visual_notes: str = Field(default="", max_length=10000)

    @field_validator("name", "description", "environment_type", "time_period", "visual_notes")
    @classmethod
    def clean_location_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def require_location_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Location name cannot be blank.")
        return value.strip()


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    environment_type: str | None = Field(default=None, max_length=40)
    time_period: str | None = Field(default=None, max_length=120)
    visual_notes: str | None = Field(default=None, max_length=10000)
    status: Literal["active", "archived"] | None = None

    @field_validator("name", "description", "environment_type", "time_period", "visual_notes")
    @classmethod
    def clean_location_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("name")
    @classmethod
    def require_location_name_when_set(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Location name cannot be blank.")
        return value.strip() if value is not None else None


class LocationRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str
    environment_type: str
    time_period: str
    visual_notes: str
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class StoryboardSceneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=10000)
    requirements: str = Field(default="", max_length=10000)
    estimated_duration_seconds: int | None = Field(default=None, gt=0, le=86400)
    location_id: uuid.UUID | None = None
    episode_id: uuid.UUID | None = None
    character_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)

    @field_validator("title", "summary", "requirements")
    @classmethod
    def clean_scene_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def require_scene_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Scene title cannot be blank.")
        return value.strip()


class StoryboardSceneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=10000)
    requirements: str | None = Field(default=None, max_length=10000)
    estimated_duration_seconds: int | None = Field(default=None, gt=0, le=86400)
    location_id: uuid.UUID | None = None
    episode_id: uuid.UUID | None = None
    character_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)

    @field_validator("title", "summary", "requirements")
    @classmethod
    def clean_scene_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("title")
    @classmethod
    def require_scene_title_when_set(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Scene title cannot be blank.")
        return value.strip() if value is not None else None


class SceneReorder(BaseModel):
    episode_id: uuid.UUID | None = None
    scene_ids: list[uuid.UUID] = Field(max_length=200)


class ScenePassageCreate(BaseModel):
    passage_text: str = Field(min_length=1, max_length=10000)
    occurrence: int = Field(default=1, ge=1, le=100)

    @field_validator("passage_text")
    @classmethod
    def validate_passage_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Passage text cannot be blank.")
        # Preserve all whitespace: the route searches for an exact source excerpt.
        return value


class ScenePassageRead(BaseModel):
    id: uuid.UUID
    reference_order: int
    start_offset: int
    end_offset: int
    passage_snapshot: str
    created_by_user_id: uuid.UUID
    created_at: datetime


ScriptElementType = Literal["action", "dialogue", "parenthetical", "transition", "production_note"]


class SceneScriptElementCreate(BaseModel):
    element_type: ScriptElementType
    content: str = Field(min_length=1, max_length=50000)
    character_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def clean_element_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Script element content cannot be blank.")
        return value.strip()

    @model_validator(mode="after")
    def validate_character_assignment(self):
        if self.element_type == "dialogue" and self.character_id is None:
            raise ValueError("Dialogue elements must identify the speaking character.")
        if self.element_type in ("action", "transition", "production_note") and self.character_id is not None:
            raise ValueError("Only dialogue and parenthetical elements may reference a character.")
        return self


class SceneScriptElementRead(BaseModel):
    id: uuid.UUID
    element_order: int
    element_type: ScriptElementType
    content: str
    character_id: uuid.UUID | None
    character_name: str | None
    created_at: datetime


class SceneScriptVersionCreate(BaseModel):
    base_version_id: uuid.UUID | None = None
    content: str | None = Field(default=None, min_length=1, max_length=50000)
    elements: list[SceneScriptElementCreate] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("content")
    @classmethod
    def clean_script_content(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Script content cannot be blank.")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_one_script_representation(self):
        has_text = self.content is not None
        has_elements = bool(self.elements)
        if has_text == has_elements:
            raise ValueError("Provide either plain-text content or a non-empty list of structured elements.")
        if self.elements and sum(len(item.content) for item in self.elements) > 50000:
            raise ValueError("Combined screenplay element text cannot exceed 50,000 characters.")
        return self


class SceneScriptVersionRead(BaseModel):
    id: uuid.UUID
    revision_number: int
    content: str
    parent_version_id: uuid.UUID | None
    author_user_id: uuid.UUID
    author_display_name: str
    created_at: datetime
    elements: list[SceneScriptElementRead] = Field(default_factory=list)


class SceneCharacterRead(BaseModel):
    id: uuid.UUID
    name: str
    role_label: str
    notes: str


class StoryboardEpisodeCreate(BaseModel):
    episode_number: int = Field(ge=1, le=1000)
    title: str = Field(min_length=1, max_length=160)
    logline: str = Field(default="", max_length=500)
    synopsis: str = Field(default="", max_length=10000)
    estimated_duration_seconds: int | None = Field(default=None, gt=0, le=86400)

    @field_validator("title", "logline", "synopsis")
    @classmethod
    def clean_episode_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def require_episode_title(cls, value: str) -> str:
        if not value:
            raise ValueError("Episode title cannot be blank.")
        return value


class StoryboardEpisodeUpdate(BaseModel):
    episode_number: int | None = Field(default=None, ge=1, le=1000)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    logline: str | None = Field(default=None, max_length=500)
    synopsis: str | None = Field(default=None, max_length=10000)
    estimated_duration_seconds: int | None = Field(default=None, gt=0, le=86400)
    status: Literal["active", "archived"] | None = None

    @field_validator("title", "logline", "synopsis")
    @classmethod
    def clean_episode_update_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("title")
    @classmethod
    def require_episode_title_when_set(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Episode title cannot be blank.")
        return value


class StoryboardEpisodeRead(BaseModel):
    id: uuid.UUID
    season_id: uuid.UUID
    episode_number: int
    title: str
    logline: str
    synopsis: str
    estimated_duration_seconds: int | None
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class StoryboardSeasonCreate(BaseModel):
    season_number: int = Field(ge=1, le=100)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    story_arc: str = Field(default="", max_length=10000)

    @field_validator("title", "description", "story_arc")
    @classmethod
    def clean_season_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def require_season_title(cls, value: str) -> str:
        if not value:
            raise ValueError("Season title cannot be blank.")
        return value


class StoryboardSeasonUpdate(BaseModel):
    season_number: int | None = Field(default=None, ge=1, le=100)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    story_arc: str | None = Field(default=None, max_length=10000)
    status: Literal["active", "archived"] | None = None

    @field_validator("title", "description", "story_arc")
    @classmethod
    def clean_season_update_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("title")
    @classmethod
    def require_season_title_when_set(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Season title cannot be blank.")
        return value


class StoryboardSeasonRead(BaseModel):
    id: uuid.UUID
    storyboard_id: uuid.UUID
    season_number: int
    title: str
    description: str
    story_arc: str
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    episodes: list[StoryboardEpisodeRead] = Field(default_factory=list)


class StoryboardSceneRead(BaseModel):
    id: uuid.UUID
    scene_order: int
    title: str
    summary: str
    requirements: str
    estimated_duration_seconds: int | None
    location_id: uuid.UUID | None
    location_name: str | None
    episode_id: uuid.UUID | None
    episode_title: str | None
    season_number: int | None
    episode_number: int | None
    characters: list[SceneCharacterRead] = Field(default_factory=list)
    passages: list[ScenePassageRead] = Field(default_factory=list)
    script_versions: list[SceneScriptVersionRead] = Field(default_factory=list)
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class StoryboardDetail(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    narrative_version_id: uuid.UUID
    narrative_version_number: int
    narrative_title: str
    narrative_content: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    scenes: list[StoryboardSceneRead] = Field(default_factory=list)
    seasons: list[StoryboardSeasonRead] = Field(default_factory=list)
    characters: list[CharacterRead] = Field(default_factory=list)
    locations: list[LocationRead] = Field(default_factory=list)
