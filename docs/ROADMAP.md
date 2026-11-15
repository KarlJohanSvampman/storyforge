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
- [x] Configure an owner-only or majority approval rule (default: owner-only).
- [x] Record append-only approve/reject vote events; the latest vote per eligible member determines the current tally.
- [x] Freeze the rule, eligible voter list, and threshold when voting first opens for a specific version.
- [x] Finalize one immutable approval or rejection decision for the exact current narrative version.
- [x] Move the project to the storyboard phase only when the owner finalizes an approval that meets the configured threshold.
- [x] Preserve vote history, decision-time tally snapshots, and project phase transition history.
- [ ] Local migration, permission, voting, rejection, approval, phase-lock, and persistence verification.

## M1 — Storyboard and creative assets

### M1.1 — Approved narrative storyboard foundation
- [x] Initialize one storyboard from the exact narrative version that triggered the approved storyboard phase transition.
- [x] Preserve separate storyboard interpretations for each approved narrative version.
- [x] Create and reorder scenes with summaries, production requirements, estimated duration, primary location, and participating story characters.
- [x] Create and update project-level character and location story-bible records.
- [x] Link scenes to exact excerpts from the immutable approved narrative, preserving offsets and excerpt snapshots.
- [x] Add append-only, optimistic-concurrency-protected working script revisions per scene.
- [ ] Local migration, API, permissions, passage-link, script revision, ordering, and persistence verification.

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
