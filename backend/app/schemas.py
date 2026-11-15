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


DocumentarySourceType = Literal[
    "article", "book", "academic_paper", "official_record",
    "government_data", "interview", "archival_record", "website", "other",
]
DocumentaryEvidenceRelation = Literal["supports", "challenges", "context"]
DocumentaryReviewResult = Literal["supported", "contested", "not_supported", "insufficient_evidence"]


class DocumentarySourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    source_type: DocumentarySourceType = "article"
    creator: str = Field(default="", max_length=500)
    publisher: str = Field(default="", max_length=240)
    publication_date: str = Field(default="", max_length=80)
    url: str | None = Field(default=None, max_length=2048)
    accessed_at: datetime | None = None
    citation_text: str = Field(default="", max_length=10000)
    research_notes: str = Field(default="", max_length=10000)

    @field_validator("title", "creator", "publisher", "publication_date", "citation_text", "research_notes")
    @classmethod
    def clean_source_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def require_source_title(cls, value: str) -> str:
        if not value:
            raise ValueError("Source title cannot be blank.")
        return value

    @field_validator("url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value else None
        if cleaned and not cleaned.startswith(("https://", "http://")):
            raise ValueError("Source URLs must begin with http:// or https://.")
        return cleaned


class DocumentarySourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    source_type: DocumentarySourceType | None = None
    creator: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=240)
    publication_date: str | None = Field(default=None, max_length=80)
    url: str | None = Field(default=None, max_length=2048)
    citation_text: str | None = Field(default=None, max_length=10000)
    research_notes: str | None = Field(default=None, max_length=10000)
    status: Literal["active", "archived"] | None = None

    @field_validator("title", "creator", "publisher", "publication_date", "citation_text", "research_notes")
    @classmethod
    def clean_source_update_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("title")
    @classmethod
    def require_source_title_when_set(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Source title cannot be blank.")
        return value

    @field_validator("url")
    @classmethod
    def validate_source_update_url(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value else None
        if cleaned and not cleaned.startswith(("https://", "http://")):
            raise ValueError("Source URLs must begin with http:// or https://.")
        return cleaned


class DocumentarySourceRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    source_type: DocumentarySourceType
    creator: str
    publisher: str
    publication_date: str
    url: str | None
    citation_text: str
    research_notes: str
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime


class DocumentaryClaimCreate(BaseModel):
    statement: str = Field(min_length=1, max_length=5000)
    context: str = Field(default="", max_length=10000)
    origin: Literal["human", "ai_assisted"] = "human"

    @field_validator("statement", "context")
    @classmethod
    def clean_claim_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("statement")
    @classmethod
    def require_claim_statement(cls, value: str) -> str:
        if not value:
            raise ValueError("Claim statement cannot be blank.")
        return value


class DocumentaryClaimUpdate(BaseModel):
    status: Literal["active", "archived"]


class DocumentaryClaimEvidenceCreate(BaseModel):
    source_id: uuid.UUID
    evidence_relation: DocumentaryEvidenceRelation
    excerpt: str = Field(default="", max_length=12000)
    locator: str = Field(default="", max_length=240)
    notes: str = Field(default="", max_length=5000)

    @field_validator("excerpt", "locator", "notes")
    @classmethod
    def clean_evidence_fields(cls, value: str) -> str:
        return value.strip()


class DocumentaryClaimReviewCreate(BaseModel):
    result: DocumentaryReviewResult
    rationale: str = Field(min_length=1, max_length=10000)

    @field_validator("rationale")
    @classmethod
    def require_review_rationale(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A review rationale is required.")
        return cleaned


class DocumentaryClaimEvidenceRead(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    source_title: str
    source_type: DocumentarySourceType
    source_url: str | None
    source_status: str
    evidence_relation: DocumentaryEvidenceRelation
    excerpt: str
    locator: str
    notes: str
    created_by_user_id: uuid.UUID
    created_at: datetime


class DocumentaryClaimReviewRead(BaseModel):
    id: uuid.UUID
    previous_status: str
    result: DocumentaryReviewResult
    rationale: str
    reviewed_evidence_snapshot: list[dict]
    reviewer_user_id: uuid.UUID
    reviewer_display_name: str
    created_at: datetime


class DocumentaryClaimRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    statement: str
    context: str
    origin: Literal["human", "ai_assisted"]
    status: str
    current_review_status: str
    created_by_user_id: uuid.UUID
    created_by_display_name: str
    created_at: datetime
    updated_at: datetime
    evidence: list[DocumentaryClaimEvidenceRead] = Field(default_factory=list)
    reviews: list[DocumentaryClaimReviewRead] = Field(default_factory=list)


class DocumentaryResearchOverview(BaseModel):
    project_id: uuid.UUID
    sources: list[DocumentarySourceRead] = Field(default_factory=list)
    claims: list[DocumentaryClaimRead] = Field(default_factory=list)


# M1.6 — documentary interview, consent, media-rights and production-reference contracts.
DocumentaryIdentityMode = Literal["named", "pseudonym", "anonymous"]
DocumentarySessionFormat = Literal["in_person", "remote", "phone", "written", "other"]
DocumentaryConsentUse = Literal[
    "research", "storyboard", "script", "narration", "lower_third",
    "caption", "promotion", "publication", "trailer", "social",
]
DocumentaryReleaseScope = Literal["project", "production", "release"]
DocumentaryReleaseStatus = Literal["draft", "signed", "withdrawn", "expired"]
DocumentaryAssetType = Literal["transcript", "audio", "video", "image", "document", "release_document", "other"]
DocumentaryRightsBasis = Literal["owned", "licensed", "public_domain", "permission", "fair_use", "research_only", "unknown"]
DocumentaryRightsStatus = Literal["active", "needs_review", "withdrawn", "superseded"]
DocumentaryClaimUsageType = Literal["outline", "scene", "script", "narration", "lower_third", "caption"]


class DocumentaryInterviewSubjectCreate(BaseModel):
    name_or_pseudonym: str = Field(min_length=1, max_length=200)
    identity_mode: DocumentaryIdentityMode = "named"
    role_or_relationship: str = Field(default="", max_length=240)
    background_notes: str = Field(default="", max_length=10000)

    @field_validator("name_or_pseudonym", "role_or_relationship", "background_notes")
    @classmethod
    def clean_subject_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("name_or_pseudonym")
    @classmethod
    def require_subject_label(cls, value: str) -> str:
        if not value:
            raise ValueError("A name or pseudonym is required.")
        return value


class DocumentaryInterviewSubjectUpdate(BaseModel):
    name_or_pseudonym: str | None = Field(default=None, min_length=1, max_length=200)
    identity_mode: DocumentaryIdentityMode | None = None
    role_or_relationship: str | None = Field(default=None, max_length=240)
    background_notes: str | None = Field(default=None, max_length=10000)
    status: Literal["active", "archived"] | None = None

    @field_validator("name_or_pseudonym", "role_or_relationship", "background_notes")
    @classmethod
    def clean_subject_update_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class DocumentaryInterviewSubjectRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name_or_pseudonym: str
    identity_mode: DocumentaryIdentityMode
    role_or_relationship: str
    background_notes: str
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentaryInterviewSessionCreate(BaseModel):
    subject_id: uuid.UUID
    session_date: datetime
    interviewer_name: str = Field(default="", max_length=200)
    session_format: DocumentarySessionFormat = "in_person"
    location_or_platform: str = Field(default="", max_length=240)
    transcript_notes: str = Field(default="", max_length=20000)

    @field_validator("interviewer_name", "location_or_platform", "transcript_notes")
    @classmethod
    def clean_session_text(cls, value: str) -> str:
        return value.strip()


class DocumentaryInterviewSessionUpdate(BaseModel):
    interviewer_name: str | None = Field(default=None, max_length=200)
    session_format: DocumentarySessionFormat | None = None
    location_or_platform: str | None = Field(default=None, max_length=240)
    transcript_notes: str | None = Field(default=None, max_length=20000)
    status: Literal["active", "archived"] | None = None

    @field_validator("interviewer_name", "location_or_platform", "transcript_notes")
    @classmethod
    def clean_session_update_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class DocumentaryInterviewSessionRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    subject_id: uuid.UUID
    subject_label: str
    session_date: datetime
    interviewer_name: str
    session_format: DocumentarySessionFormat
    location_or_platform: str
    transcript_notes: str
    status: str
    media_asset_ids: list[uuid.UUID] = Field(default_factory=list)
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentaryReleaseCreate(BaseModel):
    subject_id: uuid.UUID
    interview_session_id: uuid.UUID | None = None
    scope_type: DocumentaryReleaseScope = "project"
    scope_label: str = Field(default="", max_length=240)
    consent_scope: str = Field(min_length=1, max_length=10000)
    withdrawal_terms: str = Field(default="", max_length=10000)
    permitted_uses: list[DocumentaryConsentUse] = Field(default_factory=list, max_length=10)
    status: Literal["draft", "signed"] = "draft"
    signed_at: datetime | None = None
    expires_at: datetime | None = None
    release_document_asset_id: uuid.UUID | None = None

    @field_validator("scope_label", "consent_scope", "withdrawal_terms")
    @classmethod
    def clean_release_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_release_state(self):
        if not self.consent_scope:
            raise ValueError("Consent scope is required.")
        if self.status == "signed" and self.signed_at is None:
            raise ValueError("A signed release requires the signing date.")
        if self.status == "draft" and self.signed_at is not None:
            raise ValueError("A draft release cannot have a signing date.")
        if self.expires_at is not None and self.signed_at is not None and self.expires_at < self.signed_at:
            raise ValueError("Release expiry cannot precede its signing date.")
        if self.scope_type == "release" and not self.scope_label:
            raise ValueError("A release-scoped consent record needs a scope label.")
        return self


class DocumentaryReleaseEventRead(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    previous_status: str | None
    new_status: str
    reason: str
    created_at: datetime


class DocumentaryReleaseRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    subject_id: uuid.UUID
    subject_label: str
    interview_session_id: uuid.UUID | None
    scope_type: DocumentaryReleaseScope
    scope_label: str
    consent_scope: str
    withdrawal_terms: str
    permitted_uses: list[DocumentaryConsentUse]
    status: DocumentaryReleaseStatus
    signed_at: datetime | None
    expires_at: datetime | None
    release_document_asset_id: uuid.UUID | None
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    events: list[DocumentaryReleaseEventRead] = Field(default_factory=list)


class DocumentaryMediaRightsCreate(BaseModel):
    rights_holder: str = Field(default="", max_length=240)
    rights_basis: DocumentaryRightsBasis = "unknown"
    license_name: str = Field(default="", max_length=240)
    license_url: str = Field(default="", max_length=2048)
    territory: str = Field(default="Worldwide", min_length=1, max_length=240)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    permitted_uses: list[DocumentaryConsentUse] = Field(default_factory=list, max_length=10)
    attribution_required: bool = False
    attribution_text: str = Field(default="", max_length=5000)
    restrictions: str = Field(default="", max_length=10000)

    @field_validator("rights_holder", "license_name", "territory", "attribution_text", "restrictions")
    @classmethod
    def clean_rights_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("license_url")
    @classmethod
    def validate_license_url(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned and not cleaned.startswith(("https://", "http://")):
            raise ValueError("Licence URLs must begin with http:// or https://.")
        return cleaned

    @model_validator(mode="after")
    def validate_rights_record(self):
        if not self.territory:
            raise ValueError("A territory or jurisdiction is required.")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("Rights expiry cannot precede the effective date.")
        if self.rights_basis == "licensed" and not self.license_name:
            raise ValueError("Licensed media must identify the licence.")
        return self


class DocumentaryMediaRightsRead(BaseModel):
    id: uuid.UUID
    media_asset_id: uuid.UUID
    version_number: int
    supersedes_rights_id: uuid.UUID | None
    rights_holder: str
    rights_basis: DocumentaryRightsBasis
    license_name: str
    license_url: str
    territory: str
    valid_from: datetime | None
    valid_until: datetime | None
    permitted_uses: list[DocumentaryConsentUse]
    attribution_required: bool
    attribution_text: str
    restrictions: str
    status: DocumentaryRightsStatus
    created_by_user_id: uuid.UUID
    created_at: datetime


class DocumentaryMediaAssetRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_id: uuid.UUID | None
    interview_session_id: uuid.UUID | None
    title: str
    asset_type: DocumentaryAssetType
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    duration_seconds: int | None
    status: str
    download_url: str
    latest_rights: DocumentaryMediaRightsRead | None
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentaryClaimUsageCreate(BaseModel):
    usage_type: DocumentaryClaimUsageType
    scene_id: uuid.UUID | None = None
    script_version_id: uuid.UUID | None = None
    reference_text: str = Field(default="", max_length=10000)

    @field_validator("reference_text")
    @classmethod
    def clean_usage_reference(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_usage_target(self):
        if self.usage_type in ("scene", "script", "lower_third", "caption") and self.scene_id is None:
            raise ValueError("This usage type must identify a storyboard scene.")
        if self.usage_type == "script" and self.script_version_id is None:
            raise ValueError("A screenplay usage must identify an exact script revision.")
        if self.usage_type != "script" and self.script_version_id is not None:
            raise ValueError("Only a screenplay usage can identify a script revision.")
        return self


class DocumentaryClaimUsageRead(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    claim_statement: str
    claim_review_status: str
    usage_type: DocumentaryClaimUsageType
    scene_id: uuid.UUID | None
    scene_title: str | None
    script_version_id: uuid.UUID | None
    script_revision_number: int | None
    reference_text: str
    created_by_user_id: uuid.UUID
    created_at: datetime


class DocumentaryProductionOverview(BaseModel):
    project_id: uuid.UUID
    subjects: list[DocumentaryInterviewSubjectRead] = Field(default_factory=list)
    sessions: list[DocumentaryInterviewSessionRead] = Field(default_factory=list)
    releases: list[DocumentaryReleaseRead] = Field(default_factory=list)
    media_assets: list[DocumentaryMediaAssetRead] = Field(default_factory=list)
    claim_usages: list[DocumentaryClaimUsageRead] = Field(default_factory=list)
