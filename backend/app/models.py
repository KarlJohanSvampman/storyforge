import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["ProjectMembership"]] = relationship(back_populates="user")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("visibility IN ('private', 'unlisted', 'public')", name="ck_projects_visibility"),
        CheckConstraint("current_phase IN ('contributions', 'development', 'storyboard', 'production', 'published')", name="ck_projects_phase"),
        CheckConstraint("format IN ('movie', 'tv_series')", name="ck_projects_format"),
        CheckConstraint("category IN ('fiction', 'documentary')", name="ck_projects_category"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    logline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    genre: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="movie", nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="fiction", nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)
    current_phase: Mapped[str] = mapped_column(String(30), default="contributions", nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    memberships: Mapped[list["ProjectMembership"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    contributions: Mapped[list["StoryContribution"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_memberships_project_user"),
        UniqueConstraint("project_id", "invited_email", name="uq_project_memberships_project_invited_email"),
        CheckConstraint("role IN ('owner', 'editor', 'contributor', 'viewer')", name="ck_membership_role"),
        CheckConstraint("status IN ('active', 'invited')", name="ck_membership_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    invited_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User | None] = relationship(back_populates="memberships")


class StoryContribution(Base):
    """A participant's contribution identity; revisions preserve every submitted text."""
    __tablename__ = "story_contributions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'withdrawn')", name="ck_story_contributions_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    project: Mapped[Project] = relationship(back_populates="contributions")
    author: Mapped[User] = relationship()
    revisions: Mapped[list["ContributionRevision"]] = relationship(
        back_populates="contribution", cascade="all, delete-orphan",
        order_by="ContributionRevision.revision_number",
    )


class ContributionRevision(Base):
    """Immutable snapshot of a contribution at a point in its history."""
    __tablename__ = "contribution_revisions"
    __table_args__ = (
        UniqueConstraint("contribution_id", "revision_number", name="uq_contribution_revisions_number"),
        CheckConstraint("revision_number >= 1", name="ck_contribution_revisions_positive_number"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contribution_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("story_contributions.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    contribution: Mapped[StoryContribution] = relationship(back_populates="revisions")
    author: Mapped[User] = relationship()


class ContributionComment(Base):
    """Append-only discussion comment attached to a contribution and optional revision."""
    __tablename__ = "contribution_comments"
    __table_args__ = (
        CheckConstraint("status IN ('visible', 'hidden')", name="ck_contribution_comments_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contribution_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("story_contributions.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("contribution_revisions.id", ondelete="SET NULL"), nullable=True)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("contribution_comments.id", ondelete="SET NULL"), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="visible", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    author: Mapped[User] = relationship()


class StorySuggestion(Base):
    """A proposed change anchored to the exact contribution revision it addresses."""
    __tablename__ = "story_suggestions"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'deferred')", name="ck_story_suggestions_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contribution_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("story_contributions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("contribution_revisions.id", ondelete="RESTRICT"), nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    decisions: Mapped[list["SuggestionDecision"]] = relationship(back_populates="suggestion", cascade="all, delete-orphan")


class SuggestionDecision(Base):
    """Append-only audit record for every suggestion state transition."""
    __tablename__ = "suggestion_decisions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    suggestion_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("story_suggestions.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    suggestion: Mapped[StorySuggestion] = relationship(back_populates="decisions")
    actor: Mapped[User] = relationship()


class NarrativeDraft(Base):
    """One collaborative proposal stream per project; versions are append-only."""
    __tablename__ = "narrative_drafts"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_narrative_drafts_project"),
        CheckConstraint("current_version_number >= 0", name="ck_narrative_drafts_version_number"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    current_version_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    versions: Mapped[list["NarrativeDraftVersion"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan",
        order_by="NarrativeDraftVersion.version_number",
    )


class NarrativeDraftVersion(Base):
    """Immutable proposed narrative snapshot; approval is a later milestone."""
    __tablename__ = "narrative_draft_versions"
    __table_args__ = (
        UniqueConstraint("draft_id", "version_number", name="uq_narrative_draft_versions_number"),
        CheckConstraint("version_number >= 1", name="ck_narrative_draft_versions_positive_number"),
        CheckConstraint("status = 'proposal'", name="ck_narrative_draft_versions_proposal_only"),
        CheckConstraint("origin IN ('compiled', 'manual')", name="ck_narrative_draft_versions_origin"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposal", nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    draft: Mapped[NarrativeDraft] = relationship(back_populates="versions")
    sources: Mapped[list["DraftSourceReference"]] = relationship(
        back_populates="version", cascade="all, delete-orphan",
        order_by="DraftSourceReference.source_order",
    )


class DraftSourceReference(Base):
    """Immutable source citation plus an exact text snapshot used in one draft version."""
    __tablename__ = "draft_source_references"
    __table_args__ = (
        UniqueConstraint("version_id", "source_order", name="uq_draft_source_references_order"),
        CheckConstraint("source_order >= 1", name="ck_draft_source_references_positive_order"),
        CheckConstraint("source_kind IN ('contribution', 'accepted_suggestion')", name="ck_draft_source_references_kind"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    contribution_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("story_contributions.id", ondelete="RESTRICT"), nullable=False)
    contribution_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("contribution_revisions.id", ondelete="RESTRICT"), nullable=False)
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("story_suggestions.id", ondelete="SET NULL"), nullable=True)
    source_title: Mapped[str] = mapped_column(String(160), nullable=False)
    source_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[NarrativeDraftVersion] = relationship(back_populates="sources")



class ProjectApprovalRule(Base):
    """Project-level rule used when a narrative proposal is put to a vote."""
    __tablename__ = "project_approval_rules"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_approval_rules_project"),
        CheckConstraint("mode IN ('owner_only', 'majority')", name="ck_project_approval_rules_mode"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), default="owner_only", nullable=False)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())





class NarrativeApprovalRound(Base):
    """Frozen eligibility and threshold snapshot created when voting first opens."""
    __tablename__ = "narrative_approval_rounds"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_narrative_approval_rounds_version"),
        CheckConstraint("rule_mode IN ('owner_only', 'majority')", name="ck_narrative_approval_rounds_rule_mode"),
        CheckConstraint("eligible_voter_count >= 1", name="ck_narrative_approval_rounds_eligible_count"),
        CheckConstraint("required_votes >= 1", name="ck_narrative_approval_rounds_required_votes"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False)
    rule_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    eligible_voter_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NarrativeApprovalVoter(Base):
    """Eligible voter frozen into a specific version's approval round."""
    __tablename__ = "narrative_approval_voters"
    __table_args__ = (
        UniqueConstraint("round_id", "voter_user_id", name="uq_narrative_approval_voters_round_user"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_approval_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    role_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NarrativeApprovalVote(Base):
    """Append-only vote event. The latest vote from each eligible member is counted."""
    __tablename__ = "narrative_approval_votes"
    __table_args__ = (
        CheckConstraint("choice IN ('approve', 'reject')", name="ck_narrative_approval_votes_choice"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    choice: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NarrativeApprovalDecision(Base):
    """One immutable final decision for a specific narrative draft version."""
    __tablename__ = "narrative_approval_decisions"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_narrative_approval_decisions_version"),
        CheckConstraint("outcome IN ('approved', 'rejected')", name="ck_narrative_approval_decisions_outcome"),
        CheckConstraint("rule_mode IN ('owner_only', 'majority')", name="ck_narrative_approval_decisions_rule_mode"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    eligible_voter_count: Mapped[int] = mapped_column(Integer, nullable=False)
    approve_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reject_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectPhaseTransition(Base):
    """Append-only project phase history, linked to the narrative version when applicable."""
    __tablename__ = "project_phase_transitions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    from_phase: Mapped[str] = mapped_column(String(30), nullable=False)
    to_phase: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    narrative_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class ProjectCharacter(Base):
    """A reusable story character identity within one project, not an actor/casting record."""
    __tablename__ = "project_characters"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_project_characters_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personality_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProjectLocation(Base):
    """A reusable story location record within one project, separate from a 3D set asset."""
    __tablename__ = "project_locations"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_project_locations_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    environment_type: Mapped[str] = mapped_column(String(40), default="unspecified", nullable=False)
    time_period: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    visual_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Storyboard(Base):
    """A storyboard interpretation anchored to one approved narrative version."""
    __tablename__ = "storyboards"
    __table_args__ = (
        UniqueConstraint("project_id", "narrative_version_id", name="uq_storyboards_project_narrative"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    narrative_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoryboardSeason(Base):
    """A season within a TV-series storyboard interpretation."""
    __tablename__ = "storyboard_seasons"
    __table_args__ = (
        UniqueConstraint("storyboard_id", "season_number", name="uq_storyboard_seasons_number"),
        CheckConstraint("season_number >= 1", name="ck_storyboard_seasons_positive_number"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_storyboard_seasons_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    storyboard_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False, index=True)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    story_arc: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StoryboardEpisode(Base):
    """An episode within a season; its scenes and screenplay are authored independently."""
    __tablename__ = "storyboard_episodes"
    __table_args__ = (
        UniqueConstraint("season_id", "episode_number", name="uq_storyboard_episodes_number"),
        CheckConstraint("episode_number >= 1", name="ck_storyboard_episodes_positive_number"),
        CheckConstraint("estimated_duration_seconds IS NULL OR estimated_duration_seconds > 0", name="ck_storyboard_episodes_duration"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_storyboard_episodes_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboard_seasons.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    logline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    estimated_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StoryboardScene(Base):
    """An ordered scene plan; each TV-series scene belongs to one episode."""
    __tablename__ = "storyboard_scenes"
    __table_args__ = (
        UniqueConstraint("storyboard_id", "episode_id", "scene_order", name="uq_storyboard_scenes_episode_order"),
        Index(
            "uq_storyboard_scenes_movie_order", "storyboard_id", "scene_order",
            unique=True, postgresql_where=text("episode_id IS NULL"),
            sqlite_where=text("episode_id IS NULL"),
        ),
        CheckConstraint("scene_order >= 1", name="ck_storyboard_scenes_positive_order"),
        CheckConstraint("estimated_duration_seconds IS NULL OR estimated_duration_seconds > 0", name="ck_storyboard_scenes_duration"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    storyboard_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("storyboard_episodes.id", ondelete="RESTRICT"), nullable=True, index=True)
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requirements: Mapped[str] = mapped_column(Text, default="", nullable=False)
    estimated_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project_locations.id", ondelete="RESTRICT"), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SceneCharacterAssignment(Base):
    """Many-to-many scene participation; this does not cast or hire an actor."""
    __tablename__ = "scene_character_assignments"
    __table_args__ = (
        UniqueConstraint("scene_id", "character_id", name="uq_scene_character_assignments_pair"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboard_scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False, index=True)
    role_label: Mapped[str] = mapped_column(String(80), default="Participant", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScenePassageReference(Base):
    """Exact character-offset link into the immutable narrative version approved for this storyboard."""
    __tablename__ = "scene_passage_references"
    __table_args__ = (
        UniqueConstraint("scene_id", "reference_order", name="uq_scene_passage_references_order"),
        CheckConstraint("reference_order >= 1", name="ck_scene_passage_references_positive_order"),
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="ck_scene_passage_references_offsets"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboard_scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    passage_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SceneScriptVersion(Base):
    """Append-only working script revision for one storyboard scene."""
    __tablename__ = "scene_script_versions"
    __table_args__ = (
        UniqueConstraint("scene_id", "revision_number", name="uq_scene_script_versions_number"),
        CheckConstraint("revision_number >= 1", name="ck_scene_script_versions_positive_number"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboard_scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scene_script_versions.id", ondelete="RESTRICT"), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SceneScriptElement(Base):
    """One typed screenplay block inside an immutable script version."""
    __tablename__ = "scene_script_elements"
    __table_args__ = (
        UniqueConstraint("script_version_id", "element_order", name="uq_scene_script_elements_order"),
        CheckConstraint("element_order >= 1", name="ck_scene_script_elements_positive_order"),
        CheckConstraint(
            "element_type IN ('action', 'dialogue', 'parenthetical', 'transition', 'production_note')",
            name="ck_scene_script_elements_type",
        ),
        CheckConstraint(
            "element_type != 'dialogue' OR character_id IS NOT NULL",
            name="ck_scene_script_elements_dialogue_character",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    script_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scene_script_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    element_order: Mapped[int] = mapped_column(Integer, nullable=False)
    element_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    character_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=True)
    character_name_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentaryResearchSource(Base):
    """A project-level research source, independent of a specific storyboard or scene."""
    __tablename__ = "documentary_research_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('article', 'book', 'academic_paper', 'official_record', 'government_data', 'interview', 'archival_record', 'website', 'other')",
            name="ck_documentary_sources_type",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_sources_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="article", nullable=False)
    creator: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    publisher: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    publication_date: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    citation_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    research_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DocumentaryClaim(Base):
    """A discrete factual proposition requiring explicit human fact-check review."""
    __tablename__ = "documentary_claims"
    __table_args__ = (
        CheckConstraint("origin IN ('human', 'ai_assisted')", name="ck_documentary_claims_origin"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_claims_status"),
        CheckConstraint(
            "current_review_status IN ('unreviewed', 'needs_review', 'supported', 'contested', 'not_supported', 'insufficient_evidence')",
            name="ck_documentary_claims_review_status",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, default="", nullable=False)
    origin: Mapped[str] = mapped_column(String(20), default="human", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    current_review_status: Mapped[str] = mapped_column(String(30), default="unreviewed", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentaryClaimEvidence(Base):
    """A claim-to-source link with the exact excerpt and locator cited as evidence."""
    __tablename__ = "documentary_claim_evidence"
    __table_args__ = (
        UniqueConstraint("claim_id", "source_id", name="uq_documentary_claim_evidence_pair"),
        CheckConstraint("evidence_relation IN ('supports', 'challenges', 'context')", name="ck_documentary_evidence_relation"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_research_sources.id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_relation: Mapped[str] = mapped_column(String(20), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    locator: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentaryClaimReview(Base):
    """Append-only human review with a snapshot of the evidence visible at decision time."""
    __tablename__ = "documentary_claim_reviews"
    __table_args__ = (
        CheckConstraint(
            "result IN ('supported', 'contested', 'not_supported', 'insufficient_evidence')",
            name="ck_documentary_claim_reviews_result",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(30), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_evidence_snapshot: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentaryInterviewSubject(Base):
    """Documentary interview source identity; supports anonymised/pseudonymous attribution."""
    __tablename__ = "documentary_interview_subjects"
    __table_args__ = (
        CheckConstraint("identity_mode IN ('named', 'pseudonym', 'anonymous')", name="ck_documentary_interview_subjects_identity_mode"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_interview_subjects_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name_or_pseudonym: Mapped[str] = mapped_column(String(200), nullable=False)
    identity_mode: Mapped[str] = mapped_column(String(20), default="named", nullable=False)
    role_or_relationship: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    background_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentaryInterviewSession(Base):
    """An interview event. Transcript and media files are separately stored assets."""
    __tablename__ = "documentary_interview_sessions"
    __table_args__ = (
        CheckConstraint("session_format IN ('in_person', 'remote', 'phone', 'written', 'other')", name="ck_documentary_interview_sessions_format"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_interview_sessions_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_interview_subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    session_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interviewer_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    session_format: Mapped[str] = mapped_column(String(20), default="in_person", nullable=False)
    location_or_platform: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    transcript_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentaryMediaAsset(Base):
    """Uploaded project media. The storage key is private and never returned by the API."""
    __tablename__ = "documentary_media_assets"
    __table_args__ = (
        CheckConstraint("asset_type IN ('transcript', 'audio', 'video', 'image', 'document', 'release_document', 'other')", name="ck_documentary_media_assets_type"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_documentary_media_assets_status"),
        CheckConstraint("size_bytes > 0", name="ck_documentary_media_assets_size"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds > 0", name="ck_documentary_media_assets_duration"),
        UniqueConstraint("storage_key", name="uq_documentary_media_assets_storage_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documentary_research_sources.id", ondelete="RESTRICT"), nullable=True, index=True)
    interview_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documentary_interview_sessions.id", ondelete="RESTRICT"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), default="document", nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentaryRelease(Base):
    """Interview release/consent record with explicit purpose and revocation terms."""
    __tablename__ = "documentary_releases"
    __table_args__ = (
        CheckConstraint("scope_type IN ('project', 'production', 'release')", name="ck_documentary_releases_scope"),
        CheckConstraint("status IN ('draft', 'signed', 'withdrawn', 'expired')", name="ck_documentary_releases_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_interview_subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    interview_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documentary_interview_sessions.id", ondelete="RESTRICT"), nullable=True)
    scope_type: Mapped[str] = mapped_column(String(20), default="project", nullable=False)
    scope_label: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    consent_scope: Mapped[str] = mapped_column(Text, nullable=False)
    withdrawal_terms: Mapped[str] = mapped_column(Text, default="", nullable=False)
    permitted_uses: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_document_asset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documentary_media_assets.id", ondelete="RESTRICT"), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentaryReleaseEvent(Base):
    """Append-only audit event for consent signing, withdrawal, and expiry."""
    __tablename__ = "documentary_release_events"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    release_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_releases.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentaryMediaRights(Base):
    """Versioned rights clearance. New records supersede, rather than overwrite, prior terms."""
    __tablename__ = "documentary_media_rights"
    __table_args__ = (
        UniqueConstraint("media_asset_id", "version_number", name="uq_documentary_media_rights_version"),
        CheckConstraint("version_number >= 1", name="ck_documentary_media_rights_positive_version"),
        CheckConstraint("rights_basis IN ('owned', 'licensed', 'public_domain', 'permission', 'fair_use', 'research_only', 'unknown')", name="ck_documentary_media_rights_basis"),
        CheckConstraint("status IN ('active', 'needs_review', 'withdrawn', 'superseded')", name="ck_documentary_media_rights_status"),
        CheckConstraint("valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from", name="ck_documentary_media_rights_validity"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    media_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_media_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_rights_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documentary_media_rights.id", ondelete="RESTRICT"), nullable=True)
    rights_holder: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    rights_basis: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    license_name: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    license_url: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    territory: Mapped[str] = mapped_column(String(240), default="Worldwide", nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permitted_uses: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    attribution_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    attribution_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    restrictions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentaryClaimUsage(Base):
    """Append-only placement of a verified documentary claim in production material."""
    __tablename__ = "documentary_claim_usages"
    __table_args__ = (
        CheckConstraint("usage_type IN ('outline', 'scene', 'script', 'narration', 'lower_third', 'caption')", name="ck_documentary_claim_usages_type"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documentary_claims.id", ondelete="RESTRICT"), nullable=False, index=True)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=True, index=True)
    script_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scene_script_versions.id", ondelete="RESTRICT"), nullable=True, index=True)
    usage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Actor(Base):
    """Persistent performer profile owned by a user, independent of any production."""
    __tablename__ = "actors"
    __table_args__ = (CheckConstraint("status IN ('active', 'archived')", name="ck_actors_status"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    biography: Mapped[str] = mapped_column(Text, default="", nullable=False)
    performance_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProjectPerformanceSettings(Base):
    """Project-level controller defaults and casting constraints."""
    __tablename__ = "project_performance_settings"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_performance_settings_project"),
        CheckConstraint("default_controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_performance_settings_controller"),
        CheckConstraint("default_control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_performance_settings_mode"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    default_controller_type: Mapped[str] = mapped_column(String(30), default="ai_agent", nullable=False)
    default_control_mode: Mapped[str] = mapped_column(String(20), default="autonomous", nullable=False)
    allow_actor_reuse: Mapped[bool] = mapped_column(default=True, nullable=False)
    allow_character_recasting: Mapped[bool] = mapped_column(default=True, nullable=False)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CastingAssignment(Base):
    """Production-scoped link between one persistent Actor and one story Character."""
    __tablename__ = "casting_assignments"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'ended', 'replaced')", name="ck_casting_assignments_status"),
        CheckConstraint("controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_casting_assignments_controller"),
        CheckConstraint("control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_casting_assignments_mode"),
        Index("uq_casting_assignments_active_character", "project_id", "character_id", unique=True, postgresql_where=text("status = 'active'"), sqlite_where=text("status = 'active'")),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False, index=True)
    role_label: Mapped[str] = mapped_column(String(100), default="Cast", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    controller_type: Mapped[str] = mapped_column(String(30), nullable=False)
    controller_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    control_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    control_settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SceneRun(Base):
    """An isolated production session for one storyboard scene and its approved source."""
    __tablename__ = "scene_runs"
    __table_args__ = (
        CheckConstraint("status IN ('prepared', 'running', 'paused', 'completed', 'aborted')", name="ck_scene_runs_status"),
        CheckConstraint("authority_epoch >= 1", name="ck_scene_runs_authority_epoch"),
        Index("ix_scene_runs_project_created", "project_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    storyboard_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboards.id", ondelete="RESTRICT"), nullable=False)
    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=False, index=True)
    narrative_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("narrative_draft_versions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="prepared", nullable=False)
    authority_epoch: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CastMemberInstance(Base):
    """Immutable cast/character snapshot instantiated inside one SceneRun."""
    __tablename__ = "cast_member_instances"
    __table_args__ = (
        UniqueConstraint("scene_run_id", "character_id", name="uq_cast_member_instances_run_character"),
        CheckConstraint("instance_status IN ('ready', 'removed')", name="ck_cast_member_instances_status"),
        CheckConstraint("authority_epoch >= 1", name="ck_cast_member_instances_authority_epoch"),
        CheckConstraint("controller_type IN ('user', 'ai_agent', 'script_engine', 'system')", name="ck_cast_member_instances_controller"),
        CheckConstraint("control_mode IN ('direct', 'command', 'assisted', 'autonomous', 'scripted')", name="ck_cast_member_instances_mode"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    casting_assignment_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("casting_assignments.id", ondelete="RESTRICT"), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False)
    character_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("project_characters.id", ondelete="RESTRICT"), nullable=False)
    actor_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    character_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    role_label_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    controller_type: Mapped[str] = mapped_column(String(30), nullable=False)
    controller_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    control_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    control_settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    instance_status: Mapped[str] = mapped_column(String(20), default="ready", nullable=False)
    authority_epoch: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ControllerAssignmentEvent(Base):
    """Append-only audit trail for controller changes within a scene run."""
    __tablename__ = "controller_assignment_events"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    cast_member_instance_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cast_member_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    authority_epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_controller_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    previous_controller_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    new_controller_type: Mapped[str] = mapped_column(String(30), nullable=False)
    new_controller_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PossessionLease(Base):
    """Time-bounded exclusive authority lease for one controller and cast instance."""
    __tablename__ = "possession_leases"
    __table_args__ = (
        CheckConstraint("authority_epoch >= 1", name="ck_possession_leases_epoch"),
        CheckConstraint("expires_at > created_at", name="ck_possession_leases_expiry"),
        Index("ix_possession_leases_instance_active", "cast_member_instance_id", "revoked_at", "expires_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    cast_member_instance_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cast_member_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    authority_epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    controller_type: Mapped[str] = mapped_column(String(30), nullable=False)
    controller_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    lease_token: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4, nullable=False)
    previous_controller_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    previous_controller_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    previous_control_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PerformanceTake(Base):
    """A recorded scene performance; finalized takes are immutable."""
    __tablename__ = "performance_takes"
    __table_args__ = (
        CheckConstraint("status IN ('recording', 'finalized', 'selected', 'discarded')", name="ck_performance_takes_status"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_performance_takes_duration"),
        UniqueConstraint("scene_run_id", "take_number", name="uq_performance_takes_run_number"),
        Index("ix_performance_takes_scene_run_created", "scene_run_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scene_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scene_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    cast_member_instance_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cast_member_instances.id", ondelete="RESTRICT"), nullable=True)
    take_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), default="Take", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="recording", nullable=False)
    camera_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    state_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PerformanceEvent(Base):
    """Timestamped, ordered control/performance event within a take."""
    __tablename__ = "performance_events"
    __table_args__ = (
        UniqueConstraint("take_id", "sequence_number", name="uq_performance_events_take_sequence"),
        CheckConstraint("sequence_number >= 0", name="ck_performance_events_sequence"),
        CheckConstraint("timestamp_ms >= 0", name="ck_performance_events_timestamp"),
        CheckConstraint("event_type IN ('transform', 'gesture', 'expression', 'voice_marker', 'camera', 'cue')", name="ck_performance_events_type"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    take_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("performance_takes.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    cast_member_instance_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cast_member_instances.id", ondelete="SET NULL"), nullable=True)
    authority_epoch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class ProductionVideoAsset(Base):
    """A finalized, project-owned video deliverable."""
    __tablename__ = "production_video_assets"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_production_video_assets_size"),
        CheckConstraint("duration_ms > 0", name="ck_production_video_assets_duration"),
        CheckConstraint("width > 0 AND height > 0", name="ck_production_video_assets_dimensions"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_production_video_assets_status"),
        UniqueConstraint("storage_key", name="uq_production_video_assets_storage_key"),
        Index("ix_production_video_assets_project_created", "project_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    render_job_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("video_render_jobs.id", ondelete="RESTRICT"), nullable=False, unique=True)
    sequence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="video/mp4", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoRenderJob(Base):
    """Durable server-side transcode of a browser-captured sequence master."""
    __tablename__ = "video_render_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_video_render_jobs_status"),
        CheckConstraint("input_size_bytes > 0", name="ck_video_render_jobs_input_size"),
        CheckConstraint("output_size_bytes IS NULL OR output_size_bytes > 0", name="ck_video_render_jobs_output_size"),
        CheckConstraint("expected_duration_ms > 0", name="ck_video_render_jobs_expected_duration"),
        Index("ix_video_render_jobs_project_created", "project_id", "created_at"),
        Index("ix_video_render_jobs_status_created", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    input_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    input_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    output_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EditSequence(Base):
    """A non-destructive editorial assembly for a project."""
    __tablename__ = "edit_sequences"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'locked')", name="ck_edit_sequences_status"),
        UniqueConstraint("project_id", "name", name="uq_edit_sequences_project_name"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EditSequenceItem(Base):
    """A non-destructive clip reference into a finalized performance take."""
    __tablename__ = "edit_sequence_items"
    __table_args__ = (
        UniqueConstraint("sequence_id", "item_order", name="uq_edit_sequence_items_order"),
        CheckConstraint("item_order >= 1", name="ck_edit_sequence_items_order"),
        CheckConstraint("in_ms >= 0 AND out_ms > in_ms", name="ck_edit_sequence_items_trim"),
        CheckConstraint("transition IN ('cut', 'fade', 'dissolve')", name="ck_edit_sequence_items_transition"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    take_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("performance_takes.id", ondelete="RESTRICT"), nullable=False)
    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboard_scenes.id", ondelete="RESTRICT"), nullable=False)
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    in_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    out_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    transition: Mapped[str] = mapped_column(String(20), default="cut", nullable=False)
    title_overlay: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    effects: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    audio_cue: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EditExport(Base):
    """Immutable edit decision list snapshot generated from one sequence revision."""
    __tablename__ = "edit_exports"
    __table_args__ = (UniqueConstraint("sequence_id", "export_number", name="uq_edit_exports_number"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    export_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PerformanceAnnotation(Base):
    """Director or collaborator note anchored to a take time, event, and/or performer."""
    __tablename__ = "performance_annotations"
    __table_args__ = (
        CheckConstraint("timestamp_ms >= 0", name="ck_performance_annotations_timestamp"),
        CheckConstraint("category IN ('note', 'continuity', 'performance', 'camera', 'audio')", name="ck_performance_annotations_category"),
        CheckConstraint("status IN ('open', 'resolved')", name="ck_performance_annotations_status"),
        Index("ix_performance_annotations_take_time", "take_id", "timestamp_ms"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    take_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("performance_takes.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("performance_events.id", ondelete="SET NULL"), nullable=True)
    cast_member_instance_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cast_member_instances.id", ondelete="SET NULL"), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="note", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class ProductionMediaAsset(Base):
    """Project-owned audio source file used by one or more editorial audio clips."""
    __tablename__ = "production_media_assets"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_production_media_assets_size"),
        CheckConstraint("duration_ms IS NULL OR duration_ms > 0", name="ck_production_media_assets_duration"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_production_media_assets_status"),
        UniqueConstraint("storage_key", name="uq_production_media_assets_storage_key"),
        Index("ix_production_media_assets_project_created", "project_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AudioTrack(Base):
    """An independently mixable audio lane in an edit sequence."""
    __tablename__ = "audio_tracks"
    __table_args__ = (
        UniqueConstraint("sequence_id", "track_order", name="uq_audio_tracks_sequence_order"),
        CheckConstraint("track_order >= 1", name="ck_audio_tracks_order"),
        CheckConstraint("role IN ('dialogue', 'music', 'effects', 'ambience', 'voiceover')", name="ck_audio_tracks_role"),
        CheckConstraint("gain >= 0 AND gain <= 2", name="ck_audio_tracks_gain"),
        CheckConstraint("pan >= -1 AND pan <= 1", name="ck_audio_tracks_pan"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="effects", nullable=False)
    track_order: Mapped[int] = mapped_column(Integer, nullable=False)
    gain: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    pan: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    muted: Mapped[bool] = mapped_column(default=False, nullable=False)
    solo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AudioClip(Base):
    """A non-destructive source range placed at a position on an audio track."""
    __tablename__ = "audio_clips"
    __table_args__ = (
        UniqueConstraint("track_id", "clip_order", name="uq_audio_clips_track_order"),
        CheckConstraint("clip_order >= 1", name="ck_audio_clips_order"),
        CheckConstraint("source_in_ms >= 0 AND source_out_ms > source_in_ms", name="ck_audio_clips_source_range"),
        CheckConstraint("timeline_start_ms >= 0", name="ck_audio_clips_timeline_start"),
        CheckConstraint("gain >= 0 AND gain <= 2", name="ck_audio_clips_gain"),
        CheckConstraint("fade_in_ms >= 0 AND fade_out_ms >= 0", name="ck_audio_clips_fades"),
        Index("ix_audio_clips_track_timeline", "track_id", "timeline_start_ms"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    track_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("audio_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    media_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("production_media_assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    clip_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_in_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_out_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    timeline_start_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gain: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    fade_in_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fade_out_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class AudioRenderJob(Base):
    """Durable request to render one immutable audio-mix snapshot."""
    __tablename__ = "audio_render_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_audio_render_jobs_status"),
        CheckConstraint("output_size_bytes IS NULL OR output_size_bytes > 0", name="ck_audio_render_jobs_output_size"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_audio_render_jobs_duration"),
        Index("ix_audio_render_jobs_project_created", "project_id", "created_at"),
        Index("ix_audio_render_jobs_status_created", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("edit_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    render_manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    output_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
