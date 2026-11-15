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
- **Clear provenance:** preserve original contributions and every revision, approved narrative versions, and production interpretations separately.\n- **Release integrity:** a published release will be an immutable snapshot with its own public page, trailer, opt-in credits, ratings, and reviews; it will not change when its source project continues evolving.
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
backend/        FastAPI application and database migrations
docs/           Product and technical decisions
```

## Development status

- **M0.1:** runnable React/Vite, FastAPI, and PostgreSQL Docker Compose scaffold. The stack has been confirmed to start and the frontend successfully reaches the health endpoint.
- **M0.2:** project creation, listing, detail views, PostgreSQL persistence, membership roles, and pending invitation records are implemented on `feature/m0-2-project-foundation`.\n- **M0.3:** individual story contributions, append-only revisions, authorship, withdrawal, and a contribution workspace are implemented on `feature/m0-3-story-contributions`.\n- **M0.4:** contribution comments, revision-anchored suggestions, owner/editor decisions, and decision history are implemented on `feature/m0-4-discussion-suggestions`.
- **M0.5:** source-preserving narrative draft compilation, immutable proposal versions, exact source provenance, and a provider-independent mock compiler are implemented on `feature/m0-5-narrative-draft-compilation`. Local migration and end-to-end verification are the next step.

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
