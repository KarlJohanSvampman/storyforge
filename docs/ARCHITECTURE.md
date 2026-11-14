# Architecture — initial direction

## 1. System boundaries

StoryForge has three broad domains:

1. **Creative workspace:** projects, membership, contributions, narrative drafts, comments, suggestions, decisions, and phase progression.
2. **Production workspace:** storyboard, scripts, cast, assets, performances, takes, cameras, editing, and rendering.
3. **Publication and community:** immutable releases, public work pages, credits, trailers, ratings, reviews, discovery, and adaptation lineage.

The first implementation should focus on the creative workspace. Production and publication concepts should inform stable boundaries without pulling later-stage features into the initial implementation.

## 2. Initial M0 components

### Browser client
React + TypeScript application. It owns presentation and local interaction state, but the backend remains authoritative for persisted project state and permissions.

### API
FastAPI exposes HTTP endpoints for ordinary reads and writes. WebSockets are reserved for collaboration events that benefit from low-latency updates.

### Persistence
PostgreSQL is the source of truth for users, projects, memberships, contributions, immutable contribution revisions, narrative versions, comments, suggestions, votes, phase state, and later published releases.

Do not add Redis, object storage, or a message broker until an actual requirement justifies them.

## 3. Core modeling principles

- Use stable IDs for entities.
- Keep authorship and timestamps on user-generated contributions.
- Never overwrite a participant's original contribution; every edit creates a new immutable revision.
- Treat an AI-generated draft as a proposal with provenance, not as an approved story.
- Keep comments and suggestions addressable to a specific version and, where practical, a specific passage.
- Model approval as an explicit decision with a recorded version and decision context.
- Track project phase changes in an auditable way.
- Define permissions at project level; do not rely on hiding UI controls.
- Separate a collaborative **project** from a specific **published release**. Reviews and ratings attach to releases, never to a mutable project workspace.
- Public attribution is opt-in per participant and should not expose private account details.

## 4. Current entities

- **User:** account identity.
- **Project:** title, description, owner, current phase, visibility, timestamps.
- **ProjectMembership:** user, project, role, status.
- **StoryContribution:** project, author, title, status, timestamps.
- **ContributionRevision:** contribution, revision number, body, author, timestamp. Revisions are append-only.
- **NarrativeDraft:** project, version, body or structured content, origin, status.
- **Comment:** author, target type and ID, body, timestamps.
- **Suggestion:** author, target draft/version or passage, proposed change, status.
- **Vote:** voter, decision target, choice, timestamp.
- **PhaseTransition:** project, previous phase, next phase, actor, timestamp, rationale.
- **PublishedRelease (future):** immutable publication snapshot linked to its source project and approved narrative/production versions.
- **ReleaseCredit / ReleaseRating / ReleaseReview (future):** public attribution and audience evaluation attached to one release.

## 5. Realtime behavior

Use WebSockets for notifications such as contribution created/revised/withdrawn, comment added, suggestion submitted or resolved, vote recorded, draft proposed or approved, and project phase changed.

The websocket is a notification channel, not the source of truth. Clients must be able to reconnect and reload canonical state from the API.

## 6. AI integration

Define an application-owned interface for AI tasks rather than coupling domain services to one provider.

Initial tasks may include combining selected contributions into a draft proposal, identifying contradictions or unresolved questions, suggesting improvements, and summarizing discussion.

AI output must be stored as a proposal with provider/model metadata where available, input references, authoring context, and creation time. AI must not directly approve a narrative or silently replace user content.

## 7. Later production and publication data

Keep the project narrative separate from production interpretation. A production version references an approved narrative version while defining its own storyboard, cast assignments, scene blocking, takes, camera tracks, audio, and edit decisions.

A published release is a separately versioned snapshot with a stable public URL, publication metadata, media/trailer references, opt-in credits, and its own ratings/reviews. Revisions to the project after publication must not silently change the reviewed release. Forked adaptations retain source lineage while maintaining independent release identities and feedback.

Performance data should remain separable: body motion, facial controls, lip-sync events, audio, camera tracks, and scene events should not be flattened into a video-only artifact during authoring.

## 8. Decisions to revisit

- Markdown versus structured rich-text narrative content.
- Conflict handling for concurrent edits.
- Exact approval quorum and voting rules.
- Project roles and permission matrix.
- Public attribution and release-credit consent workflow.
- Media storage and upload pipeline.
- WebSocket scaling strategy.
- Whether rendering should happen in-browser, server-side, or both.
