# Scene Runtime, Performance Recording and Editorial Assembly

This document describes the first executable virtual-production slice. It extends the production architecture baseline without conflating a persistent Actor, a story Character, a casting decision, and a scene-local performer instance.

## Runtime identity and snapshots

- `StoryboardScene` is the authored scene plan.
- `CastingAssignment` is the current production-level actor-to-character relationship and controller policy.
- `SceneRun` is one isolated execution of one scene. It snapshots the scene description, approved narrative version, latest screenplay revision, passage references, and location at creation.
- `CastMemberInstance` is a run-local instance derived from the active casting assignment for a character participating in that scene. Actor, character and initial controller details are copied into snapshots so later profile edits or recasting do not rewrite an existing run.

A scene run is created only in the production phase. Every active character assigned to the scene must have an active casting assignment. The run lifecycle is:

`ready → running ↔ paused → completed`

A ready run can also be abandoned. Completed and abandoned runs are terminal. A new attempt creates a new SceneRun with a higher per-scene run number; runs are never reset in place.

## Production phase handoff

The project owner activates production after a storyboard exists, at least one scene exists, and all active characters referenced by the storyboard have active casting assignments. The transition is recorded in the existing append-only project phase history. Production runtime writes are restricted to project owners and editors; project members can inspect runtime and take history.

## Controller authority and possession

Each CastMemberInstance has an integer `authority_epoch`. Every controller handoff increments the epoch and appends a `ControllerAssignmentEvent`. A client must associate commands/events with the epoch it was granted; unknown epochs are rejected.

A `PossessionLease` is a short-lived (5–120 second) direct-control grant bound to the instance and its current authority epoch. The assigned human performer may possess their character; a project owner/editor may temporarily possess an AI- or script-controlled character as director. Acquisition snapshots the previous controller and control mode, increments the epoch, and temporarily assigns direct human control. Release or expiry restores the previous controller only if the lease still owns the current epoch. A later explicit controller handoff supersedes the lease and prevents it from restoring stale authority. Run completion releases leases and restores their previous controller where the lease remains authoritative.

The database is the authority for controller assignment and lease validity. A lease token is not a substitute for project membership checks.

## Performance recording

A `PerformanceTake` belongs to one SceneRun and stores a state snapshot, event count, duration, and editorial status (`recorded`, `selected`, or `rejected`). `PerformanceTakeEvent` records a typed event with an increasing order, monotonic millisecond timestamp, optional CastMemberInstance reference, authority epoch, and JSON payload.

Examples include character transforms, blocking markers, dialogue/performance cues, and virtual-camera cuts. Camera presets are captured in the take snapshot and camera changes are appended as ordered events. The current browser MVP supports manual event entry and camera-preset event capture; it does not yet stream physics transforms or animation samples at frame rate. High-frequency capture belongs in a future streaming layer, not one relational database write per rendered frame.

Selected and rejected takes are immutable. At most one take is selected for a given storyboard scene; selecting another take returns the former selection to recorded status. Replay clients can reconstruct the starting snapshot and apply events in order. Controller authority epochs are preserved as part of the event record.

## Editorial assembly

An `EditSequence` is a non-destructive project-level assembly. Each `EditSequenceItem` references a selected take and stores source in/out points, sequence order, transition (`cut`, `fade`, `dissolve`), title overlay, effect metadata, and an audio cue. Editing increments the sequence revision and never mutates the source take.

Export creates an immutable `EditExport` snapshot containing a revision-stamped edit decision list (EDL): source take references, clip trims, timeline positions, transitions, title/effect metadata, audio cues, and total duration. The JSON EDL is downloadable and can be consumed by a future conform/render worker.

**Explicit current boundary:** EDL export is not a rendered movie. Actual audio asset management, track mixing/synchronization, media conform, compositing, and final video rendering remain future work. The 3D viewport currently provides a simple set and procedural stand-in rigs, not production-ready character assets, animation retargeting, or physics simulation.

## API surface

All routes are scoped below `/api/projects/{project_id}/production`.

- `POST /activate` — owner-controlled storyboard-to-production transition.
- `POST /scene-runs`, `GET /scene-runs`, `GET /scene-runs/{run_id}`, `PATCH /scene-runs/{run_id}` — create, inspect, and transition scene runs.
- `POST /scene-runs/{run_id}/instances/{instance_id}/controller` — append a controller handoff and advance authority epoch.
- `GET /scene-runs/{run_id}/controller-events` — inspect controller history.
- `POST /scene-runs/{run_id}/instances/{instance_id}/lease` and lease `/renew`, `/release` routes — acquire, renew, and release direct possession.
- `POST /scene-runs/{run_id}/takes`, `GET /takes`, `GET /takes/{take_id}`, `POST /takes/{take_id}/events`, `PATCH /takes/{take_id}` — record, inspect, append to, and select/reject takes.
- `POST /edit-sequences`, `GET /edit-sequences`, `GET /edit-sequences/{sequence_id}` — manage assemblies.
- `POST /edit-sequences/{sequence_id}/items`, `PATCH /edit-sequences/{sequence_id}/items/{item_id}`, `DELETE /edit-sequences/{sequence_id}/items/{item_id}`, `PUT /edit-sequences/{sequence_id}/reorder` — edit the timeline.
- `POST /edit-sequences/{sequence_id}/export`, `GET /exports/{export_id}` — create and retrieve immutable EDL snapshots.

## Operational boundaries and next work

- The current authentication dependency is the repository's fixed development identity. It must be replaced before public deployment.
- The browser viewport is Three.js; scene/run/cast/take/edit metadata remains backend-authoritative.
- Next technical work: realtime transport for high-frequency performance capture, full virtual-camera rig and shot metadata, production-grade character rigs/animation, media/audio asset references, and an actual render/conform pipeline.
