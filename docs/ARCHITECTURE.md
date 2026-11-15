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
- **NarrativeDraft:** one project-level proposal stream, with a current version counter.
- **NarrativeDraftVersion:** immutable title/content snapshot, author, parent version, proposal status, origin, and optional provider/model/template metadata.
- **DraftSourceReference:** ordered provenance link to an exact contribution revision or accepted suggestion, plus a snapshot of the source title and text.
- **ProjectApprovalRule:** a project's owner-only or majority approval policy.
- **NarrativeApprovalRound:** the frozen voting rule, eligible voter count, and threshold for one exact narrative version.
- **NarrativeApprovalVoter:** the user and role snapshot for each member eligible in a specific approval round.
- **NarrativeApprovalVote:** append-only vote events for an exact immutable narrative version.
- **NarrativeApprovalDecision:** one final approved/rejected decision per narrative version, including a snapshot of the rule and tally.
- **ProjectPhaseTransition:** append-only history of project phase changes, linked to the narrative version where applicable.
- **Comment:** author, target type and ID, body, timestamps.
- **Suggestion:** author, target draft/version or passage, proposed change, status.
- **PublishedRelease (future):** immutable publication snapshot linked to its source project and approved narrative/production versions.
- **ReleaseCredit / ReleaseRating / ReleaseReview (future):** public attribution and audience evaluation attached to one release.
- **ActorProfile (future):** a public performer identity that may be created and managed by a user, including users who do not create stories themselves.
- **ActorManagement (future):** a manager-to-actor relationship with explicit authority and consent.
- **ActorCredit (future):** a performer's credited participation in a release or production, forming the actor's public track record.
- **ProductionBudget / BudgetLedgerEntry (future):** a production's budget configuration and auditable record of estimated, committed, and actual costs.
- **CastingEngagement (future):** a production-specific booking of an actor, including the quoted and agreed fee captured at booking time.

## 5. Realtime behavior

Use WebSockets for notifications such as contribution created/revised/withdrawn, comment added, suggestion submitted or resolved, vote recorded, draft proposed or approved, and project phase changed.

The websocket is a notification channel, not the source of truth. Clients must be able to reconnect and reload canonical state from the API.

## 6. AI integration

Define an application-owned interface for AI tasks rather than coupling domain services to one provider.

Initial tasks may include combining selected contributions into a draft proposal, identifying contradictions or unresolved questions, suggesting improvements, and summarizing discussion.

AI output must be stored as a proposal with provider/model metadata where available, input references, authoring context, and creation time. AI must not directly approve a narrative or silently replace user content.

### M0.5 compilation contract

The first compiler is deliberately deterministic and source-preserving. It assembles selected contribution revisions into a readable proposal without claiming to summarize, reconcile, or improve their content. This gives the project a working end-to-end draft workflow while the provider boundary is established.

- A compile request identifies exact immutable contribution revision IDs. It may additionally identify accepted suggestions, but only when each suggestion is accepted and anchored to the selected revision.
- Withdrawn contributions cannot be selected for a new compilation.
- The compiler is an application-owned protocol. Its initial implementation reports provider `mock`, model `source-preserving-assembler-v1`, and template `assembly-template-v1`; no external AI service or API key is required in M0.5.
- Each compile action creates a new immutable proposal version. It records parent version, author, timestamp, origin, provider/model/template metadata, and ordered source references.
- Each source reference retains an exact text snapshot and identifiers for the contribution, revision, and optional suggestion. The snapshot remains understandable even if a participant later changes their contribution.
- Manual edits create another immutable version rather than changing the compiled version. The new version inherits its parent's source map and links to its parent.
- Every M0.5 version has status `proposal`. There is no approval endpoint, voting, publication, or phase transition in this milestone. M0.6 owns those decisions.
- Project members can read the draft. Owners, editors, and contributors can compile or revise it; viewers are read-only. These rules are enforced by the API, not only by the UI.

### M0.6 approval and phase progression contract

- A project has one approval rule. If no rule has been explicitly saved, the effective default is `owner_only`. The owner can select `owner_only` or `majority`.
- Under `owner_only`, only the project owner may cast the approval vote; one approve or reject vote meets the threshold.
- Under `majority`, active owners, editors, and contributors are eligible. Viewers and pending invitations are excluded. The threshold is a strict majority: `floor(eligible_members / 2) + 1`.
- When the first vote is cast on a version, create a ballot snapshot containing the rule mode, exact eligible voter IDs/roles, eligible count, and required threshold. Later membership or project-rule changes must not silently rewrite that ballot. The project rule is locked once the ballot opens.
- Each vote is an append-only event. A participant may change their vote before a final decision; only their latest vote counts in the tally. Earlier votes remain visible in history.
- The owner alone finalizes the result once either approve or reject reaches the threshold. A split or incomplete tally cannot be finalized. The final decision records the exact narrative version, rule mode, eligible voter count, approval/rejection counts, required threshold, actor, note, and timestamp.
- A decision is unique to one immutable narrative version. Only the current draft version can be voted on or finalized. A rejected version remains rejected; participants can create another proposal version and vote on that new version.
- A rejected decision does not change the project phase. An approved decision atomically records the decision and transitions the project to `storyboard`, with a `ProjectPhaseTransition` entry referencing the approved version.
- Once the project enters `storyboard`, narrative compilation, manual draft revision, voting, and approval-rule changes are blocked. The approved narrative version remains available as the authoritative input for M1.
- Approval rules become locked after the first vote, preventing a rule change from altering a tally already in progress.
- The client may display and submit votes, but all eligibility checks, tally calculations, finalization, and phase changes are enforced by the API.

## 7. Later production and publication data

Keep the project narrative separate from production interpretation. A production version references an approved narrative version while defining its own storyboard, cast assignments, scene blocking, takes, camera tracks, audio, and edit decisions.

A published release is a separately versioned snapshot with a stable public URL, publication metadata, media/trailer references, opt-in credits, and its own ratings/reviews. Revisions to the project after publication must not silently change the reviewed release. Forked adaptations retain source lineage while maintaining independent release identities and feedback.

Performance data should remain separable: body motion, facial controls, lip-sync events, audio, camera tracks, and scene events should not be flattened into a video-only artifact during authoring.

## 8. Actor marketplace and production economics (future)

StoryForge may support a performer ecosystem alongside its creator community. Any user, whether or not they write or produce stories, can create one or more actor personas and manage them. Actor profiles are public, IMDb-style portfolios with a stable identity, biography, image/media, skills, availability/preferences, representation/manager information where consented, and verified credits from published productions. A manager is a user acting on behalf of an actor; the relationship and its permissions must be explicit, revocable, and auditable. An actor may self-manage or appoint a manager.

Actor identity is distinct from account identity. The public profile should not expose private account details. A user may manage multiple actor personas, and the same actor persona may later be portrayed by its owner or controlled by an AI performer agent. Human and AI performers should use compatible casting/credit contracts while clearly disclosing the performer type. Future workflows may let users direct and perform alongside AI-controlled actors.

### Economic model principles

- Treat production economics as a first-class simulation system, not as a hidden quality score or arbitrary penalty system.
- Every production should display a budget, committed costs, actual costs, remaining budget, and eventual gross revenue, even when the project uses an effectively unlimited or sandbox budget.
- Costs should be explicit ledger entries linked to the action or resource that caused them: casting/actor fees, crew, locations, props, sets, equipment, production time, post-production, and reshoots/retakes where applicable.
- A retake is not inherently a score penalty. It may create an additional cost because it consumes production resources; the amount should be explainable and configurable.
- Actor hiring fees may grow as an actor gains credits, experience, audience demand, or reputation. Keep the pricing calculation explainable and snapshot the quoted/agreed fee on each casting engagement so later price changes do not rewrite historical budgets.
- Do not confuse production cost with artistic quality. A costly production is not automatically better; ratings and audience response remain separate measures.
- Views can later drive simulated gross revenue using a published, transparent revenue model. Gross revenue, production cost, and net result must remain separate metrics.
- Support an unlimited-budget mode for low-friction creative play, but continue recording notional costs and revenue so productions can be compared economically if desired.
- Use virtual/in-game budgets and revenue only unless a separate real-money feature is deliberately designed, reviewed, and consented to. No real-money payout is implied by these systems.

The first implementation should not build an actor marketplace, dynamic hiring prices, budgets, or revenue calculations yet. It should avoid hard-coding the idea that retakes are a score deduction. Production actions should eventually emit cost events into a ledger, with the budget and pricing policies applied by a separate economics service.

## 9. Decisions to revisit

- Markdown versus structured rich-text narrative content.
- Conflict handling for concurrent edits.
- Exact approval quorum and voting rules.
- Project roles and permission matrix.
- Public attribution and release-credit consent workflow.
- Media storage and upload pipeline.
- WebSocket scaling strategy.
- Whether rendering should happen in-browser, server-side, or both.
- Actor profile ownership, manager permissions, performer consent, and public-credit verification.
- Actor fee formula, rate-card snapshots, cost categories, and budget modes.
- View-to-revenue conversion and whether revenue is only a simulation metric.
- How human-controlled and AI-controlled actors share casting, performance, and credit contracts.
