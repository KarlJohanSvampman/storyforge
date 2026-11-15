# Roadmap

## Working method
Work in small, demonstrable increments. Each milestone should produce something runnable and testable. Prefer a vertical slice over broad scaffolding.

## M0 — Collaborative storytelling

### M0.1 — Runnable skeleton
- [x] React + TypeScript frontend starts locally.
- [x] FastAPI backend starts locally.
- [x] Frontend can call a health endpoint.
- [x] Docker Compose runs the stack.
- [x] README contains exact setup instructions.

### M0.2 — Projects
- [x] Create and list projects.
- [x] View project details.
- [x] Define basic project membership and roles.
- [x] Persist data in PostgreSQL.
- [x] Record pending collaborator invitations (email delivery and acceptance deferred).

### M0.3 — Individual story contributions
- [x] Participants submit independent story contributions.
- [x] Contributions display author and creation time.
- [x] Every edit creates an immutable revision; original text is preserved.
- [x] Project participants can read contributions according to membership permissions.
- [x] Authors can revise or withdraw their own contributions; owners/editors can moderate project contributions.
- [ ] Local migration, API, and UI verification.

### M0.4 — Discussion and suggestions
- [x] Add comments to contributions, optionally anchored to a specific revision.
- [x] Submit a proposed alternative anchored to an exact contribution revision.
- [x] Allow owners/editors to accept, reject, or defer suggestions.
- [x] Preserve comment history and append-only suggestion decision history.
- [ ] Local migration, API, permission, and UI verification.

### M0.5 — Draft compilation and AI seam
- [x] Create a combined narrative draft from selected contributions.
- [x] Record exact contribution revisions and optional accepted suggestions used by each draft version.
- [x] Provide a provider-independent compiler interface with a deterministic source-assembly implementation.
- [x] Store compiled output as an unapproved proposal with provider/model/template metadata.
- [x] Allow a participant to edit and submit a new immutable proposal version while carrying forward provenance.
- [ ] Local migration, API, permission, concurrency, and UI verification.

### M0.6 — Approval and phase progression
- [ ] Configure a simple project approval rule.
- [ ] Record votes and approval decisions.
- [ ] Approve a specific immutable narrative version.
- [ ] Move the project to the storyboard phase only after approval.
- [ ] Show phase and decision history.

## M1 — Storyboard and creative assets
- [ ] Convert an approved narrative into ordered scenes.
- [ ] Define scene summaries, participants, requirements, and estimated duration.
- [ ] Create basic character and location records.
- [ ] Connect scenes to relevant story passages and script material.

## M2 — Basic virtual production
- [ ] Render a simple 3D set and rigged characters.
- [ ] Provide virtual cameras and basic character performance recording.
- [ ] Store takes as structured, replayable data.

## M3 — Editing and finished-film workflow
- [ ] Select takes, cut scenes, arrange sequences, and manage audio.
- [ ] Add basic transitions, titles, and simple effects.
- [ ] Export a rendered film.

## M4 — Publication and public work pages
- [ ] Create immutable published releases from approved project versions.
- [ ] Give each release a permanent public page with poster/cover, synopsis, trailer, release date, and media.
- [ ] Add opt-in contributor, cast, and production credits with role labels.
- [ ] Preserve release snapshots when the underlying project continues evolving.

## M5 — Ratings, reviews, and discovery
- [ ] Allow one editable 1–10 rating per user per release.
- [ ] Add written reviews, spoiler controls, reactions, and reporting.
- [ ] Display aggregate score, rating count, and rating distribution.
- [ ] Add discovery by genre, popularity, recency, and creator.
- [ ] Add moderation and anti-brigading safeguards.

## M6 — Actor profiles and production economics
- [ ] Allow any user to create one or more actor personas, whether or not they create content.
- [ ] Add public performer profiles with biographies, media, skills, availability, and published credits.
- [ ] Allow users to manage actors through explicit, revocable manager relationships.
- [ ] Support casting offers and fee snapshots, with explainable rates influenced by credits, experience, and demand.
- [ ] Add production budgets and an auditable ledger for estimated, committed, and actual costs.
- [ ] Track retakes and other production actions as resource costs rather than arbitrary quality-score deductions.
- [ ] Add configurable unlimited-budget mode that still displays notional costs.
- [ ] Track views and simulated gross revenue separately from costs, ratings, and artistic quality.
- [ ] Design compatible casting contracts for human-controlled and AI-controlled performers.

## M7 — Adaptations and lineage
- [ ] Fork projects while preserving source lineage.
- [ ] Compare alternative storyboards and scene interpretations.
- [ ] Link adaptation releases to source works.
- [ ] Separate automated production metrics from human audience ratings.

## M8 — Advanced capture and immersive tools
- [ ] Improve webcam body and face tracking.
- [ ] Add manual facial performance tools and lip-sync refinement.
- [ ] Add WebXR acting and camera operation where supported.

## Definition of done for M0
A small group can create a project, submit individual contributions, discuss and suggest changes, produce a combined draft, approve a specific version, and see the project move to the storyboard phase. The workflow must preserve authorship and history.

## Deferred
Do not implement webcam tracking, facial capture, WebXR, character rigs, virtual cameras, editing, actor marketplace, budgets, dynamic hiring prices, revenue calculations, or public review features during M0. Keep future requirements in mind without building speculative infrastructure. Production economics must be designed as a cost ledger, not as a disguised scoring system.
