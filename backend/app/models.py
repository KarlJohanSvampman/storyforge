import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
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
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    logline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    genre: Mapped[str] = mapped_column(String(80), default="", nullable=False)
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


class StoryboardScene(Base):
    """An ordered scene plan; the script is revised separately in append-only versions."""
    __tablename__ = "storyboard_scenes"
    __table_args__ = (
        UniqueConstraint("storyboard_id", "scene_order", name="uq_storyboard_scenes_order"),
        CheckConstraint("scene_order >= 1", name="ck_storyboard_scenes_positive_order"),
        CheckConstraint("estimated_duration_seconds IS NULL OR estimated_duration_seconds > 0", name="ck_storyboard_scenes_duration"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    storyboard_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False, index=True)
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
