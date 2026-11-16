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

### M1.2 — Structured screenplay
- [x] Represent each scene script revision as ordered action, dialogue, parenthetical, transition, and production-note elements.
- [x] Attribute dialogue to an active story character assigned to the scene, preserving the character-name snapshot in each immutable revision.
- [x] Render structured blocks into a readable screenplay while preserving the typed element records.
- [x] Edit, add, remove, and reorder screenplay blocks in the browser.
- [x] Keep M1.1 plain-text script revisions readable and support converting them into a new structured revision without changing the original.
- [ ] Local migration, screenplay validation, speaker assignment, revision concurrency, and persistence verification.

### M1.3 — Project formats and TV-series structure
- [x] Add independent project format (movie, tv_series) and content category (fiction, documentary) fields with backward-compatible defaults.
- [x] Add TV-series seasons and episodes within each storyboard interpretation.
- [x] Attach each TV-series scene to an episode and scope scene ordering to that episode.
- [x] Preserve existing movie scenes as project-level scenes with no episode assignment.
- [x] Add browser workflows to create seasons/episodes and archive/restore them without deleting scene or script history.
- [ ] Local migration, API permissions, movie compatibility, series hierarchy, scene assignment, ordering, and persistence verification.

### M1.4 — Documentary research and claim-level fact-checking
- [x] Add a documentary source register with bibliographic metadata, URLs, citations, access timestamps, notes, and archive/restore controls.
- [x] Add discrete documentary claims with human/AI-assisted origin labels.
- [x] Link claims to exact supporting, challenging, or contextual evidence excerpts with page/section/timecode locators.
- [x] Add append-only human review decisions with rationale, reviewer identity, and evidence snapshots.
- [x] Invalidate a current fact-check when evidence is added or a cited source is changed/archived, preserving prior review history.
- [x] Enforce source/evidence requirements for supported, contested, and not-supported outcomes.
- [ ] Local migration, API permission, source/evidence integrity, review invalidation, and persistence verification.

### M1.5 — Reusable story-bible management
- [x] Edit character profiles: name, story description, visual description, and personality notes.
- [x] Edit location profiles: name, environment type, time period, description, and visual notes.
- [x] Archive and restore characters and locations without deleting their project-level records.
- [x] Preserve existing scene references and script history when a character or location is archived.
- [x] Keep archived existing references editable on their scenes while blocking new assignments until restored.
- [x] Keep screenplay name snapshots immutable when story-bible character names change.
- [ ] Local UI/API permission, existing-reference, archive/restore, name-snapshot, and persistence verification.

### M1.6 — Documentary interviews, media and rights
- [x] Add interview subjects with named, pseudonymous, and anonymous identity modes, plus dated interview sessions and notes.
- [x] Track draft/signed releases, explicit consent scope, permitted uses, expiry, signed-document references, and append-only withdrawal events.
- [x] Add archival/interview media provenance, rights holder, licence/basis, territory, validity, duration, attribution and permitted-use records, with version history.
- [x] Support private source-file uploads with size/type validation, SHA-256 checksums, project membership access, and a dedicated persistent storage volume.
- [x] Link currently supported claims into documentary outlines, scenes, exact screenplay revisions, narration, lower-thirds, and captions.
- [ ] Local migration, upload/download access, consent withdrawal, rights enforcement, claim placement, and persistence verification.

## M2 — Basic virtual production

### M2.0 — Actor and casting foundation
- [x] Separate persistent user-owned Actor profiles from project-owned story Characters.
- [x] Add production-scoped CastingAssignments with active/replaced/ended history.
- [x] Allow an actor to portray multiple characters unless project settings prohibit reuse.
- [x] Configure project-level default controller type and control mode, with per-casting overrides.
- [x] Separate controller identity (user, AI agent, script engine, system) from control mode (direct, command, assisted, autonomous, scripted).
- [x] Validate human controllers against active project membership and actor ownership before casting.
- [x] Preserve casting history and prevent archiving actors with active assignments.
- [x] Add browser casting workspace, actor talent library, production cast, controller inspector, and project performance policy.
- [x] Expand integration coverage for actor ownership boundary, project isolation, recasting, reuse policy, blank role labels, and controller validation.

### M2.1 — Scene runtime foundation
- [x] Create isolated SceneRuns from storyboard scenes, snapshotting the exact storyboard narrative version and active casting assignments into CastMemberInstances.
- [x] Add authority epochs, append-only controller assignment history, and time-bounded possession lease storage.
- [x] Add lease acquisition/renewal/revocation and authority-epoch enforcement endpoints, including temporary director possession and restoration of prior control.
- [x] Render an interactive Three.js set with procedural character stand-ins and selectable virtual camera presets.
- [x] Add owner-controlled storyboard-to-production phase activation with scene/casting readiness checks.

### M2.2 — Performance and recording
- [x] Add take lifecycle and timestamped, sequenced performance-event capture API with camera-state snapshots.
- [x] Store finalized takes as structured, replayable data.
- [x] Add browser-based virtual camera controls, take recording, event capture, and take finalization/selection UI.
- [x] Add finalized-take replay endpoint with immutable scene/cast snapshots and ordered event stream.\n- [x] Add browser play/pause, event stepping, timeline scrubbing, transform interpolation and camera-preset reconstruction for supported payloads.\n- [x] Add timecoded director annotations with author identity, event/performer anchors, and resolution state.\n- [ ] Add side-by-side take comparison, higher-frequency capture, deterministic physics replay, and skeletal animation reconstruction.

## M3 — Editing and finished-film workflow
- [x] Select takes and arrange non-destructive scene clips in an editable sequence.
- [x] Support source trims, clip reordering, cut/fade/dissolve transitions, title overlays, effect metadata, and audio cues.
- [x] Export immutable, revision-stamped JSON edit decision lists (EDLs).
- [ ] Manage actual audio media, tracks, mixing, and synchronization.
- [ ] Render and export a finished video file.

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
