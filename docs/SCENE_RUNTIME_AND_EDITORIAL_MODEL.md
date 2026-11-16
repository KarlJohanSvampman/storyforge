# Virtual Production Runtime and Editorial Workflow

This document describes the current M2.1–M3 implementation, building on the canonical SceneRun and PerformanceTake models already present in StoryForge.

## M2.1 — Scene runtime

A `StoryboardScene` is an authored plan. A `SceneRun` is one isolated execution of that scene and is populated from the current active casting assignments. Each `CastMemberInstance` is scoped to one run and snapshots the actor name, character name, role label, controller type, controller user and control mode. Recasting a project character later does not rewrite existing scene-run instances.

Run lifecycle:

`prepared → running ↔ paused → completed`

A prepared run can also be aborted. Completed and aborted runs are terminal; another attempt creates a new run. Production runtime writes are restricted to project owners and editors.

The owner moves a storyboard-phase project into production through an explicit handoff. The handoff requires a storyboard, at least one scene, and active casting assignments for every active character referenced by the storyboard. The phase change is recorded in the existing phase-history table.

## Controller authority and possession

Every cast-member instance has an `authority_epoch`. A controller handoff increments the epoch and appends a `ControllerAssignmentEvent`. Performance events referencing a cast instance must include an epoch known in that instance's controller history; unknown epochs are rejected.

A possession lease is short-lived and bound to one cast instance and authority epoch. The assigned human performer may possess their character; an owner/editor may temporarily possess an AI- or script-controlled character as director. Acquisition snapshots the previous controller and control mode, increments the epoch, and temporarily assigns direct human control. Release or expiry restores the previous controller only if the lease still owns the current epoch. A later explicit controller handoff supersedes the lease and prevents stale restoration. Run completion releases active leases and restores their prior controller where possible.

## M2.2 — Performance takes

A `PerformanceTake` belongs to one SceneRun and stores a title, camera snapshot, state snapshot, duration, and status (`recording`, `finalized`, `selected`, or `discarded`). `PerformanceEvent` stores a typed event, monotonically increasing sequence number, timestamp in milliseconds, optional cast-member instance reference, authority epoch, and JSON payload.

Supported event types include transforms, gestures, expressions, voice markers, camera changes and cues. Selected/finalized takes are immutable. Selecting a take for editorial use deselects the previous selected take for that storyboard scene. Event data can be retrieved in sequence for a future deterministic playback/reconstruction layer.

The browser MVP provides a live Three.js set, selectable virtual-camera presets, manual structured event entry, and camera-cut recording. Finalized takes expose an ordered replay payload with their original state/camera snapshots and cast-member identity snapshots. The browser supports play/pause, seeking, stepping between events, position interpolation between transform samples, rotation/scale application, and camera-preset changes.

Replay is deliberately capability-aware: it reconstructs only data explicitly present in event payloads. It does not claim deterministic physics replay, continuous capture between recorded events, skeletal animation, lip-sync, or audio playback. A take with sparse manually entered events will therefore show sparse motion.

Director annotations are timecoded to a take and can optionally reference a performance event or cast-member instance. Notes retain author identity and open/resolved state; owners/editors can resolve notes, while collaborators can create and edit their own notes.

## M3 — Editorial assembly

An `EditSequence` is a non-destructive project-level assembly. Each `EditSequenceItem` references a selected take and stores source in/out points, sequence order, transition (`cut`, `fade`, `dissolve`), title overlay, effect metadata, and an audio cue. Editing increments the sequence revision; the source take is never modified.

Export creates an immutable `EditExport` snapshot containing a revision-stamped edit decision list (EDL): source take references, source trims, timeline positions, transitions, title/effect metadata, audio cues, and total duration. The browser downloads this manifest as JSON.

**Important boundary:** an EDL is not a rendered movie. Actual audio media/track management, mixing and synchronization, media conform, compositing, and final video rendering are future work.

## M3.2 — Media and audio pipeline

Production audio assets are project-scoped, content-hashed files stored outside the public web root. Uploads accept common browser-decodable audio formats and are limited to 250 MiB per file. Download endpoints require active project membership; storage keys are never exposed.

An `AudioTrack` belongs to one draft edit sequence and has a role (dialogue, music, effects, ambience, or voiceover), order, gain, pan, mute and solo state. An `AudioClip` references an immutable source asset and stores source in/out points, timeline start, clip gain and fade-in/fade-out durations. Source media is not modified by editing.

The browser audio timeline supports overlapping clips across tracks. Its Web Audio preview schedules clips against the sequence millisecond clock, applies track and clip gain, stereo pan, mute/solo state, source offsets and fade envelopes, and supports seeking while preserving synchronization. The audio timeline is preview-only: it does not create a mastered audio file.

EDL format version 2 adds audio track and clip snapshots, source asset identifiers, checksums, content types, download routes, source ranges, timeline positions, gains, pans, mute/solo state and fade automation. The export remains an immutable instruction manifest, not a rendered audio or video file.

## M3.3 — Offline audio rendering

An audio render request creates a durable `AudioRenderJob` containing a revision-stamped, immutable snapshot of all audible tracks and clips. The snapshot records source asset identifiers and private storage keys, source ranges, timeline offsets, track/clip gain, stereo pan, mute/solo selection, fades, output sample rate and total duration. Later edits to the sequence do not alter a queued render.

A dedicated Docker worker claims queued jobs with a database row lock and renders the mix through FFmpeg to 48 kHz, stereo, 24-bit PCM WAV. It applies source trimming, timeline delay, gain, pan, fade envelopes, summing, padding to the planned timeline duration and a final limiter. Completed outputs are stored in the shared production-media volume and recorded with size, SHA-256 checksum and duration. Project members can poll job state and download completed WAVs through authenticated routes.

Jobs move through queued, running, completed or failed states. Failures retain a bounded diagnostic message. A render is a master audio deliverable only; it does not render video, and it does not mutate source media or the edit sequence.

## M4.0 — Browser sequence video export

The Production Studio can render an ordered draft edit sequence in the browser. It loads replay data for each selected take, switches the persistent Three.js viewport between scenes, advances the take-local playhead through the selected source in/out range, reconstructs supported transform and camera events, and draws title overlays into the captured WebGL canvas.

The canvas is captured at 30 fps through `HTMLCanvasElement.captureStream` and recorded with `MediaRecorder` to WebM. A completed offline WAV master can be decoded with Web Audio and attached as a synchronized audio stream in the same recording. The browser reports progress, supports cancellation, and downloads the resulting file locally; the video is not uploaded to the project server.

Cuts are direct. Fade and dissolve edit instructions are currently approximated as fade-through-black. Effects metadata, deterministic physics, skeletal animation, persistent video assets, MP4/H.264 encoding, server-side rendering and true cross-dissolve compositing remain future work. Output resolution is based on the active viewport's drawing-buffer size, and export duration is real-time.

## Main API routes

- `POST /api/projects/{project_id}/production/activate` — owner-controlled phase handoff.
- `POST /api/projects/{project_id}/scene-runs`, `GET /api/projects/{project_id}/scene-runs` — prepare/list scene runs.
- `PATCH /api/projects/{project_id}/scene-runs/{run_id}` — run lifecycle.
- `POST /api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/controller` — controller handoff.
- `POST /api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/leases` — acquire direct possession; companion `/renew` and `/release` routes manage the lease.
- `POST /api/projects/{project_id}/scene-runs/{run_id}/takes`, `POST /api/projects/{project_id}/takes/{take_id}/events`, `POST /api/projects/{project_id}/takes/{take_id}/finalize`, `POST /api/projects/{project_id}/takes/{take_id}/select` — record and select takes.
- `POST /api/projects/{project_id}/edit-sequences`, `POST /api/projects/{project_id}/edit-sequences/{sequence_id}/items`, `PATCH/DELETE .../items/{item_id}`, `PUT .../reorder`, `POST .../export` — assemble and export EDLs.

## Next work

- Event-stream playback/reconstruction and higher-frequency realtime transport.
- Production-quality character rigs, animation retargeting, and physics-driven performances.
- Actual audio assets/tracks, mixing, and synchronization.
- A conform/render worker capable of producing a finished video file from EDLs and source media.
