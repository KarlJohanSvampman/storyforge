# The StoryForge Collective

**Many minds. Many stories. Endless interpretations.**

The StoryForge Collective is a browser-first platform for collaborative storytelling and virtual filmmaking. Participants create a story together, develop it into a production plan, and can eventually perform, direct, edit, publish, and adapt it.

The project is being developed incrementally. The first milestone focuses on collaborative storytelling; 3D production, motion capture, and VR come later.

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
- **Clear provenance:** preserve original contributions, approved narrative versions, and production interpretations separately.
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
| Realtime collaboration | WebSockets |
| Background jobs / ephemeral coordination | Redis, when needed |
| Media and asset storage | S3-compatible object storage, when needed |
| AI | Provider-independent service adapter |
| Motion capture | Browser-compatible tracking, evaluated in a later milestone |
| VR | WebXR, later milestone |
| Local development | Docker Compose |

These are starting choices, not irreversible commitments. Keep dependencies justified and avoid introducing infrastructure before a use case needs it.

## Milestones

### M0 — Collaborative storytelling

- Create projects and manage participants.
- Collect individual story contributions.
- Present a combined draft without losing source contributions.
- Support comments and proposed changes.
- Support voting and explicit approval.
- Track project phase and narrative versions.

### M1 — Storyboard and creative assets

- Convert an approved story into ordered scenes.
- Define scene summaries, participants, requirements, and estimated duration.
- Create basic character and location records.
- Connect scenes to relevant story passages and script material.

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
backend/        FastAPI application
docs/           Product and technical decisions
```

The repository will grow with the implementation. Avoid creating empty abstractions or speculative modules merely to fill out a planned directory tree.

## Development status

**Status: M0.1 bootstrap implemented on `feature/m0-1-runnable-skeleton`.** The initial React/Vite frontend, FastAPI health endpoint, Docker Compose stack, and local development guide are in place. This is a runnable scaffold, not yet a collaborative storytelling product.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the first delivery plan and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for initial architectural boundaries.

## Development

See [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) for prerequisites, startup commands, service URLs, and troubleshooting. Start the stack from the repository root with `docker compose up --build`.

## Naming

Product: **StoryForge**  
Community / project identity: **The StoryForge Collective**  
Tagline: **Many minds. Many stories. Endless interpretations.**
