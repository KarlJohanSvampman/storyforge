# Architecture — initial direction

## 1. System boundaries

StoryForge has three broad domains:

1. **Creative workspace:** projects, membership, contributions, narrative drafts, comments, suggestions, decisions, and phase progression.
2. **Production workspace:** storyboard, scripts, cast, assets, performances, takes, cameras, editing, and rendering.
3. **Evaluation and lineage:** project versions, adaptations, production metrics, audience feedback, and comparisons.

The first implementation should focus on the creative workspace. Production concepts should not dictate the shape of the initial storytelling domain.

## 2. Initial M0 components

### Browser client

React + TypeScript application. It owns presentation and local interaction state, but the backend remains authoritative for persisted project state and permissions.

### API

FastAPI exposes versioned HTTP endpoints for ordinary reads and writes. WebSockets are reserved for collaboration events that benefit from low-latency updates.

### Persistence

PostgreSQL is the source of truth for users, projects, memberships, contributions, narrative versions, comments, suggestions, votes, and phase state.

Do not add Redis, object storage, or a message broker until an actual M0 requirement justifies them.

## 3. Core modeling principles

- Use stable IDs for entities.
- Keep authorship and timestamps on user-generated contributions.
- Never overwrite a participant's original contribution when generating a combined draft.
- Treat an AI-generated draft as a proposal with provenance, not as an approved story.
- Keep comments and suggestions addressable to a specific version and, where practical, a specific passage.
- Model approval as an explicit decision with a recorded version and decision context.
- Track project phase changes in a way that can be audited.
- Define permissions at project level; do not rely on hiding UI controls.

## 4. Suggested initial entities

These are conceptual starting points, not final database schemas:

- **User:** account identity.
- **Project:** title, description, owner, current phase, visibility, timestamps.
- **ProjectMembership:** user, project, role, status.
- **StoryContribution:** author, project, body, status, timestamps.
- **NarrativeDraft:** project, version, body or structured content, origin, status.
- **Comment:** author, target type and ID, body, timestamps.
- **Suggestion:** author, target draft/version or passage, proposed change, status.
- **Vote:** voter, decision target, choice, timestamp.
- **PhaseTransition:** project, previous phase, next phase, actor, timestamp, rationale.

A later iteration should decide whether narrative content is stored as Markdown, structured blocks, or both. Start with the simplest representation that supports passage-level discussion without premature complexity.

## 5. Realtime behavior

Use WebSockets for notifications such as:

- contribution created
- comment added
- suggestion submitted or resolved
- vote recorded
- draft proposed
- draft approved
- project phase changed

The websocket is a notification channel, not the source of truth. Clients should be able to reconnect and reload canonical state from the API.

## 6. AI integration

Define an application-owned interface for AI tasks rather than coupling domain services to one provider.

Initial tasks may include:

- combine selected contributions into a draft proposal
- identify contradictions or unresolved questions
- suggest improvements
- summarize discussion

AI output must be stored as a proposal with model/provider metadata where available, input references, authoring context, and creation time. AI must not directly approve a narrative or silently replace user content.

## 7. Later production data

When production work begins, keep the project narrative separate from production interpretation. A production version can reference an approved narrative version while defining its own storyboard, cast assignments, scene blocking, takes, camera tracks, audio, and edit decisions.

Performance data should remain separable: body motion, facial controls, lip-sync events, audio, camera tracks, and scene events should not be flattened into a video-only artifact during authoring.

## 8. Decisions to revisit

- Markdown versus structured rich-text narrative content.
- Conflict handling for concurrent edits.
- Exact approval quorum and voting rules.
- Project roles and permission matrix.
- Media storage and upload pipeline.
- WebSocket scaling strategy.
- Whether rendering should happen in-browser, server-side, or both.
