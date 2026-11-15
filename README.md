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
| 3D | Three.js, introduced with the virtual-production milestone |
| Backend | Python + FastAPI |
| Database | PostgreSQL, introduced with persistent project data |
| Realtime collaboration | WebSockets, when needed |
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

- Establish actor, character, casting, runtime-instance, and controller relationships.
- Support player, director, AI, and scripted control.
- Provide semantic performance commands and basic navigation/gesture execution.
- Build the Director's Studio with a Three.js viewport, cast panel, inspector, blocking tools, and performance controls.
- Provide virtual cameras and basic character performance recording.
- Store takes as structured, replayable data.

See [docs/PRODUCTION_PERFORMANCE_ARCHITECTURE.md](docs/PRODUCTION_PERFORMANCE_ARCHITECTURE.md) for the production-domain decisions and staged implementation order.

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

## Development

### Run with Docker Compose

Requirements: Docker Desktop or Docker Engine with the Docker Compose plugin.

From the repository root:

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- API health: http://localhost:8000/api/v1/health

The frontend container serves the built React application through Nginx and proxies `/api/` requests to FastAPI. The development Vite server uses the same `/api/` path and proxies it to the local backend.

Stop the stack with:

```bash
docker compose down
```

### Run services separately

Backend:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies API calls to http://127.0.0.1:8000.

### Backend tests

From the repository root, with the development requirements installed:

```bash
python -m pytest backend/tests
```

### Current implementation boundary

The initial code provides the frontend shell, FastAPI application, health endpoint, Docker Compose wiring, and a health-endpoint test. It does not yet implement project creation, membership, contributions, comments, narrative drafts, approval, or production features. PostgreSQL is intentionally not added until the persistent project milestone.

## Naming

Product: **StoryForge**  
Community / project identity: **The StoryForge Collective**  
Tagline: **Many minds. Many stories. Endless interpretations.**
