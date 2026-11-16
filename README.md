# The StoryForge Collective

**Many minds. Many stories. Endless interpretations.**

The StoryForge Collective is a browser-first platform for collaborative storytelling and virtual filmmaking. Participants create a story together, develop it into a production plan, and can eventually perform, direct, edit, publish, and adapt it.

The project is being developed incrementally. The first milestone focuses on collaborative storytelling and preserving the history of each participant’s contributions. 3D production, publication, motion capture, and VR follow later.

## Product vision

A project moves through a sequence of creative and production phases:

1. Story contributions
2. Story development and approval
3. Storyboard and scene breakdown
4. Characters and cast
5. Locations, sets, and props
6. Script and dialogue
7. Music and sound
8. Scene production and direction
9. Editing and post-production
10. Publication, evaluation, and adaptations

Not every project must use every phase. Projects should be able to skip or revisit phases where appropriate.

## Guiding principles

- **Collaborative by design:** participants contribute, discuss, suggest, and make decisions together.
- **Human creative control:** AI assists but does not silently decide or overwrite group-approved creative work.
- **Clear provenance:** preserve original contributions and every revision, approved narrative versions, and production interpretations separately.
- **Release integrity:** a published release will be an immutable snapshot with its own public page, trailer, opt-in credits, ratings, and reviews; it will not change when its source project continues evolving.
- **Browser first:** the core application should work without installing a native client.
- **Production as editable data:** performances, facial animation, audio, cameras, and scene state should remain independently editable rather than being flattened immediately into video.
- **Adaptable stories:** a completed project can be forked into independent adaptations while retaining a link to its source.
- **Incremental delivery:** build a useful end-to-end slice before investing in advanced production tooling.

## Initial technical direction

| Area | Initial choice |
|---|---|
| Frontend | React + TypeScript |
| 3D | Three.js |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM / migrations | SQLAlchemy + Alembic |
| Realtime collaboration | WebSockets |
| Background jobs / ephemeral coordination | Redis, when needed |
| Media and asset storage | S3-compatible object storage, when needed |
| AI | Provider-independent service adapter |
| Motion capture | Browser-compatible tracking, evaluated in a later milestone |
| VR | WebXR, later milestone |
| Local development | Docker Compose |

## Milestones

### M0 — Collaborative storytelling

- Create projects and manage participants.
- Collect individual story contributions.
- Present a combined draft without losing source contributions.
- Support comments and proposed changes.
- Support voting and explicit approval.
- Track project phase and narrative versions.

### M1 — Storyboard and creative assets

- Create projects as movies or TV series, independently classified as fiction or documentary.
- For TV series, organise work into seasons and episodes, with each episode owning its own scenes and screenplay.
- Convert an approved story into ordered scenes.
- Define scene summaries, participants, requirements, and estimated duration.
- Create and maintain reusable character and location story-bible records, with profile editing and archive/restore controls.
- Connect scenes to relevant story passages and script material.

Documentary is a first-class category for either a movie or a series. The research workspace now records sources, factual claims, claim-level evidence excerpts, and append-only human fact-check decisions. Interview releases, archival-media rights, source-file storage, and claim-to-scene/script integration remain planned work.

### M2 — Basic virtual production

- Render a simple 3D set and rigged characters.
- Provide virtual cameras and basic character performance recording.
- Store takes as structured, replayable data.

### M3 — Editing and finished-film workflow

- Select takes, cut scenes, arrange sequences, and manage audio.
- Add basic transitions, titles, and simple effects.
- Export a rendered film.

### M4 — Adaptations and evaluation

- Fork projects while preserving lineage.
- Compare alternative storyboards and scene interpretations.
- Separate automated production metrics from human audience ratings.

### M5 — Advanced capture and immersive tools

- Improve webcam body and face tracking.
- Add manual facial performance tools and lip-sync refinement.
- Add WebXR acting and camera operation where supported.

## Repository layout

```
frontend/       Browser application
backend/        FastAPI application and database migrations
docs/           Product and technical decisions
```

## Development status

- **M0.1–M0.6:** the runnable application foundation, project workspace, contributions, discussion, narrative compilation, approval and phase progression are integrated into `main`.
- **M1.1–M1.2:** storyboard foundation and structured screenplay are integrated into `main`.
- **M1.3:** movie/TV-series formats, fiction/documentary categories, and season/episode structure are integrated into `main`.
- **M1.4:** documentary source registers, factual claims, excerpt-level evidence, and append-only human fact-check reviews are integrated into `main`.
- **M1.5:** reusable character/location story-bible editing and archive/restore are integrated into `main`.
- **M1.6:** documentary interviews, consent/release records, private media uploads, versioned rights records, and supported-claim production references are integrated into `main`.
- **M2.0:** actor profiles, production casting assignments, project performance defaults, and per-character controller configuration are implemented on the M2 development branch; pending merge and browser casting workspace.

The M0–M1.6 application milestones are integrated into `main`. GitHub Actions CI is active and the latest run passed the full Alembic migration chain, backend API integration tests, and frontend TypeScript/Vite production build. Manual browser-based end-to-end, real media-volume restart/backup, and production-security verification remain outstanding. Upload storage is local to a dedicated Docker volume; coordinate database and media-volume backups. The fixed development identity is not suitable for public deployment.


The current local identity is a fixed development-only user. Authentication, invitation email delivery, and invitation acceptance are intentionally not enabled yet. Do not deploy this development configuration publicly.

See [docs/ROADMAP.md](docs/ROADMAP.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md).

## Development

From the repository root, run:

```bash
docker compose up --build
```

Open http://localhost:5173 for the frontend and http://localhost:8000/docs for the API documentation.

## Naming

Product: **StoryForge**  
Community / project identity: **The StoryForge Collective**  
Tagline: **Many minds. Many stories. Endless interpretations.**


## Virtual production status

- **M2.1:** Scene runs, cast-member instances, per-instance authority epochs, controller history, possession leases with temporary director takeover/restoration, production phase handoff, and a Three.js set viewport are implemented.
- **M2.2:** Timestamped performance events, take finalization, replay snapshots, event seeking, supported transform/camera reconstruction, and timecoded director notes are implemented. Deterministic physics and skeletal animation replay remain future work.
- **M3.1:** Non-destructive edit sequences support clip trims, ordering, transitions, title/effect metadata, and immutable JSON EDL export.
- **M3.2:** Project audio assets, multitrack editing, source/timeline trims, gain, pan, mute/solo, fade automation, browser mix preview and audio-aware EDL v2 are implemented.
- **M3.3:** Durable FFmpeg audio-render jobs produce downloadable 48 kHz stereo 24-bit WAV masters from immutable mix snapshots.
- **M4.0:** The Production Studio captures ordered selected takes from its Three.js viewport as WebM, reconstructs supported transform/camera events, draws title overlays and can mux a completed WAV master.
- **M4.1:** Browser captures upload into durable project-scoped video jobs. A dedicated FFmpeg worker verifies source integrity, encodes H.264/AAC MP4, probes output metadata and stores immutable video assets with checksums and authenticated downloads.
- **M4.2:** A browser-independent 2D animatic renderer snapshots selected takes, scene/cast metadata and ordered performance events from an exact EDL revision. It reconstructs transforms and camera framing, composites titles and transitions, and stores an MP4 as a normal production video asset.
- **M4.3:** A dedicated Playwright/Chromium worker renders immutable scene manifests through Three.js WebGL without using the user's browser. The interactive viewport and headless renderer share the same procedural character-rig builder; the headless stage includes 3D set geometry, lighting, camera reconstruction, transforms, titles and transitions. Production asset import, skeletal animation, physics replay and audio conform remain future work.

See [Scene Runtime and Editorial Model](docs/SCENE_RUNTIME_AND_EDITORIAL_MODEL.md) for the data contracts and boundaries.


## Production 3D asset library (M4.4)

Projects can store versioned, immutable glTF 2.0 assets in a project-scoped library. Uploads accept self-contained `.glb` files or JSON `.gltf` documents with embedded data-URI resources; external URLs and relative resource paths are rejected so an asset cannot make the renderer fetch arbitrary network or filesystem resources. Uploads are limited to 250 MiB (25 MiB for JSON glTF documents), hashed with SHA-256, and stored in the persistent `storyforge_assets` volume.

Character and location models can be assigned to project characters and locations. Prop models are retained as reusable library entries. Re-uploading an asset name creates a new immutable version and updates the current binding; prior versions remain available for reproducible render manifests. Asset list, metadata, binding and download endpoints are project-membership protected. Viewers may read assets but cannot upload, archive or change bindings.

The current milestone establishes the registry, validation, storage and binding contracts. The next renderer integration milestone consumes the selected immutable asset versions in both the interactive and headless Three.js scene builders.
