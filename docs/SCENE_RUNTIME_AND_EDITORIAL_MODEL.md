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

The canvas is captured at 30 fps through `HTMLCanvasElement.captureStream` and recorded with `MediaRecorder` to WebM. A completed offline WAV master can be decoded with Web Audio and attached as a synchronized audio stream in the same recording. The browser reports capture progress and supports cancellation.

The WebM master is uploaded to a durable `VideoRenderJob` tied to the exact edit-sequence revision. A dedicated Docker worker verifies the input SHA-256 and encodes H.264/yuv420p video with AAC audio into an MP4 using FFmpeg. FFprobe validates the result and extracts duration and dimensions. Completed files become immutable `ProductionVideoAsset` records with content hashes, size, dimensions, revision provenance and authenticated project-scoped download URLs. Jobs have queued, running, completed and failed states; stale jobs can be recovered after worker interruption.

This milestone moves encoding and delivery to the server, but scene composition is still captured by the browser. It is not yet a headless EDL renderer. Cuts are direct; fade and dissolve edit instructions are approximated as fade-through-black. Effects metadata, deterministic physics, skeletal animation, native dissolve compositing, configurable render profiles and poster generation remain future work.

## M4.1 — Persistent video export pipeline

- `POST /api/projects/{project_id}/edit-sequences/{sequence_id}/video-renders` — upload a WebM master and queue server-side MP4 encoding. The request must match the current draft sequence revision.
- `POST /api/projects/{project_id}/edit-sequences/{sequence_id}/scene-renders` — snapshot selected takes and queue a headless animatic render from recorded performance data.
- `GET /api/projects/{project_id}/edit-sequences/{sequence_id}/video-renders` — list render jobs and their processing state.
- `GET /api/projects/{project_id}/production/videos` — list completed project video assets.
- `GET /api/projects/{project_id}/production/videos/{asset_id}/download` — download a stored MP4 asset.
- `GET /api/projects/{project_id}/video-renders/{job_id}/download` — download the MP4 output for a completed render job.

## M4.2 — Headless animatic rendering

`POST /api/projects/{project_id}/edit-sequences/{sequence_id}/scene-renders` creates a revision-locked `VideoRenderJob` without a browser upload. The API verifies every edit item references a selected take in the same project and scene, then snapshots scene names, cast-member identity snapshots, camera/state snapshots, event streams, trims, titles, effects metadata and transition settings. The manifest is stored with the job, so later edits cannot change an in-progress render.

The video worker supports two render sources: `webm_upload` (the M4.1 browser capture/transcode path) and `headless_animatic`. For headless jobs, the worker renders 1280×720 frames at 24 fps with Pillow, reconstructing position/rotation/scale from timestamped transform events and interpolating between samples. Camera presets and simple camera offsets affect framing. Each scene receives a scene label and optional title overlay. Cuts, fade-through-black and cross-dissolves are composited at the frame level. FFmpeg encodes the resulting frame sequence to H.264/yuv420p MP4, after which the existing asset pipeline records dimensions, duration, size and SHA-256 and exposes authenticated project downloads.

This is a deterministic 2D animatic renderer using procedural stand-ins, not a 3D scene renderer. It is intended to validate blocking, timing, recorded transforms and editorial transitions without a browser, WebGL, or a user-uploaded video. The current API caps headless exports at ten minutes; the frame renderer accepts 12, 24 or 30 fps and up to 1920×1080 manifests, while the API currently selects 1280×720 at 24 fps. Full 3D assets, skeletal animation, physics, native effects, audio conform and configurable render profiles remain future work.

## M4.3 — Headless Three.js production rendering

The Production Studio offers a second server-render mode through the existing revision-locked scene-render endpoint:

- POST /api/projects/{project_id}/edit-sequences/{sequence_id}/scene-renders?renderer=3d — create a headless_3d job from the same immutable selected-take manifest used by the 2D animatic path.
- POST /api/projects/{project_id}/edit-sequences/{sequence_id}/scene-renders — retain the original Pillow-based 2D animatic renderer.

The 3D job is processed by the dedicated video-renderer image, based on the Playwright Python/Chromium image. The worker loads the internal Vite-served headless-render.html entry point, passes the database-snapshotted manifest directly into the page, advances an integer frame index at the manifest frame rate, and captures PNG frames. No user browser session, public manifest URL, uploaded WebM, or client-side capture is involved. The worker composites the rendered frame sequence through FFmpeg and uses the existing MP4 probe, checksum, asset persistence, and authenticated download pipeline.

frontend/src/productionScene.ts is the shared Three.js scene runtime. It creates the 3D set, lighting, camera, title overlay and procedural character rigs. ThreeSceneViewport uses the same character-rig builder as the headless renderer, keeping the visible interactive performers and offline render stand-ins consistent. The renderer reconstructs transform samples at source-trimmed frame times, applies camera snapshot/event state, and composites cut, fade-through-black and cross-dissolve transitions between rendered 3D frames.

This is a genuine headless Three.js/WebGL render path, using Chromium's software WebGL implementation in the worker container. At M4.3 the current geometry and character bodies were procedural blocking stand-ins. M4.4 added the project-scoped GLB/GLTF asset registry, and M4.5 connects static character/location meshes to the interactive and headless renderers. Skinned rigs, skeletal animation clips, retargeting, facial animation, physics replay, and audio conform remain future work. The 3D renderer supports 1280×720 at 24 fps from the current API manifest and retains the ten-minute frame budget. The 2D animatic path remains available as a lighter preview option.

## Main API routes

- `POST /api/projects/{project_id}/production/activate` — owner-controlled phase handoff.
- `POST /api/projects/{project_id}/scene-runs`, `GET /api/projects/{project_id}/scene-runs` — prepare/list scene runs.
- `PATCH /api/projects/{project_id}/scene-runs/{run_id}` — run lifecycle.
- `POST /api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/controller` — controller handoff.
- `POST /api/projects/{project_id}/scene-runs/{run_id}/cast-members/{instance_id}/leases` — acquire direct possession; companion `/renew` and `/release` routes manage the lease.
- `POST /api/projects/{project_id}/scene-runs/{run_id}/takes`, `POST /api/projects/{project_id}/takes/{take_id}/events`, `POST /api/projects/{project_id}/takes/{take_id}/finalize`, `POST /api/projects/{project_id}/takes/{take_id}/select` — record and select takes.
- `POST /api/projects/{project_id}/edit-sequences`, `POST /api/projects/{project_id}/edit-sequences/{sequence_id}/items`, `PATCH/DELETE .../items/{item_id}`, `PUT .../reorder`, `POST .../export` — assemble and export EDLs.

## Next work

- Skeletal animation clips, retargeting, facial animation, and deterministic physics replay.
- Audio conform that combines the completed WAV master with the headless 3D picture render.
- Native effect processing, configurable render profiles, persistent thumbnails/posters, and scalable render scheduling.


## M4.5 — Renderer asset integration

The M4.4 asset registry is consumed by both Three.js render paths. A character or location binding selects one immutable ProductionAsset version. Binding placement is stored independently as a transform object:

- position: three world/local coordinates in scene units.
- rotation: three Euler angles in radians.
- scale: three positive scale components.

The binding transform endpoint accepts partial updates and validates finite values and supported ranges. A render request resolves the current bindings while its edit sequence is locked and copies the asset ID, kind, target, version, checksum, file format, content type, byte size, storage key and transform into each applicable clip. The render job never re-queries the mutable binding when it executes.

The interactive viewport loads the selected character/location models through the authenticated project download endpoint. Character models follow their cast-member transform and replace the procedural body while preserving the cast label. Location models are loaded only for the active scene's location. Scenes without an assigned model retain the existing procedural stand-in.

The headless renderer uses the same productionScene.ts loader and placement logic. The video-renderer container mounts the asset volume read-only. Playwright intercepts the internal asset URLs and fulfills only files explicitly named by the immutable manifest; the resolved path must remain inside the asset root and the file's SHA-256 must match the snapshot. GLB and self-contained GLTF data-URI resources are supported without external network or filesystem fetches.

M4.5 covers static glTF scene graphs and root placement. It does not yet reconstruct glTF skeletal animation clips, retarget animation, simulate deterministic physics, place unbound props, or conform audio to the headless 3D render.


## M4.1 — Immutable publication releases

A release is an append-only publication record linked to a project, one storyboard interpretation, its exact approved narrative version, and one completed production video asset. Release creation is owner-only and is allowed while the project is in the production phase.

The published_releases row stores a project-local release number, permanent unique slug, release title and synopsis, visibility snapshot, source IDs, publisher identity, publication timestamp, and a JSON manifest. The manifest freezes project metadata, narrative title/content/provider provenance, approval-decision identity, storyboard seasons and episodes, ordered scene plans, location descriptions, assigned story characters, and the latest structured screenplay revision and elements for each scene. It also freezes the chosen MP4's ID, SHA-256, dimensions, duration, source edit-sequence revision and render-job provenance.

Before publication, the API verifies that the storyboard belongs to the project, its exact narrative version has an approved decision, the video asset belongs to the project and is active, its render job is completed and agrees with the asset's checksum/storage key, and the stored video bytes still match the recorded SHA-256. The selected sequence must also belong to the project.

The release list/detail endpoints are currently membership-protected. There are intentionally no update or delete routes. Public and unlisted read/playback routes, posters/trailers and opt-in credits are deferred to M4.2/M4.3. Release visibility is copied at publication time; changing project visibility later cannot silently change an existing release's intended visibility.
