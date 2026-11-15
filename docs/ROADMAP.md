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
- [ ] Add comments to contributions and drafts.
- [ ] Submit a suggestion referencing a target.
- [ ] Accept, reject, or defer a suggestion.
- [ ] Preserve discussion history.

### M0.5 — Draft compilation and AI seam
- [ ] Create a combined narrative draft from selected contributions.
- [ ] Record which contributions informed the draft.
- [ ] Provide an AI provider interface, initially with a deterministic/mock implementation.
- [ ] Store AI output as an unapproved proposal.
- [ ] Allow a participant to edit and submit a revised proposal.

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

## M6 — Adaptations and lineage
- [ ] Fork projects while preserving source lineage.
- [ ] Compare alternative storyboards and scene interpretations.
- [ ] Link adaptation releases to source works.
- [ ] Separate automated production metrics from human audience ratings.

## M7 — Advanced capture and immersive tools
- [ ] Improve webcam body and face tracking.
- [ ] Add manual facial performance tools and lip-sync refinement.
- [ ] Add WebXR acting and camera operation where supported.

## Definition of done for M0
A small group can create a project, submit individual contributions, discuss and suggest changes, produce a combined draft, approve a specific version, and see the project move to the storyboard phase. The workflow must preserve authorship and history.

## Deferred
Do not implement webcam tracking, facial capture, WebXR, character rigs, virtual cameras, editing, scoring, or public review features during M0. Keep future requirements in mind without building speculative infrastructure.
