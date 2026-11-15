# Local development

## Requirements

- Docker Desktop (or Docker Engine) with the Compose plugin.
- Git.

Node.js and Python are not required on the host when using Docker Compose.

## Start the application

From the repository root:

```bash
docker compose up --build
```

On backend startup, Alembic applies any pending database migrations before Uvicorn starts.

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

The frontend uses the Vite development server. Requests to `/api` are proxied to the backend container, so browser code can call the API using relative paths.

## M0.2 project workflow

The local app provides a development-only Storyteller identity so project features can be exercised before authentication is implemented.

- Create a project from **My projects**.
- Open a project to see its details and current phase.
- The creator becomes its owner.
- Owners can record pending invitations with an email address and a role (editor, contributor, or viewer).
- Project data and memberships persist in PostgreSQL across container restarts.

The invitation endpoint records a pending invitation only. It does not send email or grant access before acceptance. Account authentication, invitation acceptance, and email delivery are later work.

The development identity is configured in `docker-compose.yml` using `STORYFORGE_AUTH_MODE=development`, `STORYFORGE_DEV_USER_EMAIL`, and `STORYFORGE_DEV_USER_NAME`. It is not authentication and must not be used for a public deployment.

## API endpoints

- `GET /api/health` — service health.
- `GET /api/projects` — projects available to the current development user.
- `POST /api/projects` — create a project.
- `GET /api/projects/{id}` — project details and membership list.
- `PATCH /api/projects/{id}` — update project details (owner/editor).
- `POST /api/projects/{id}/invitations` — record a pending invitation (owner only).


## M0.5 narrative draft workflow

The draft workspace is available inside each project. The first compiler is intentionally source-preserving and does not call an external AI provider.

- Add at least one active contribution to a project.
- Use the **Combined story draft** section to select the contribution revisions to include.
- Accepted suggestions anchored to the selected current revisions appear beneath their contributions and can be included optionally.
- Select **Assemble draft proposal**. The resulting proposal shows each selected source in order and preserves exact source references and text snapshots.
- Select **Revise proposal** to edit the current proposal. Saving creates a new immutable version; it does not overwrite the prior version.
- Use **Proposal history** to inspect earlier compiled or manually revised versions. Older versions are read-only in this milestone.
- Restart the containers and reopen the project to confirm that draft versions and provenance persist.

The mock compiler only combines the selected contribution and accepted-suggestion text into sections. It does not summarize, reconcile contradictions, or make creative decisions. The provider interface is ready for a later AI-backed implementation, but no AI key or provider is used by M0.5. All versions remain proposals; approval and phase progression are M0.6.

### M0.5 API endpoints

- `GET /api/projects/{project_id}/draft` — return the project's draft history, or `null` when no draft exists.
- `POST /api/projects/{project_id}/draft/compile` — create a new proposal version from exact contribution revision IDs and optional accepted suggestion IDs.
- `POST /api/projects/{project_id}/draft/{draft_id}/versions` — create a manual revision based on the current version. A stale base version returns HTTP 409.
- `GET /api/projects/{project_id}/contributions/{contribution_id}/suggestions` — list suggestions and their decision history.

### M0.5 verification checklist

1. Compile a draft from two or more active contributions.
2. Confirm that withdrawn contributions are unavailable for selection and rejected/deferred suggestions cannot be included.
3. Accept a suggestion, include it in a new compilation, and confirm its source reference is labelled as an accepted suggestion.
4. Revise one of the original contributions and compile again. Confirm the older draft version still contains its earlier source text snapshot.
5. Manually revise the current proposal. Confirm a new version is created, the earlier version remains in history, and provenance is carried forward.
6. Submit a manual version based on an older version through the API and confirm it returns HTTP 409.
7. Restart Docker Compose and confirm the draft and its version/source history persist.

The current fixed development identity makes multi-user role testing limited. API authorization still checks project membership and denies write operations to viewers, but a separate authenticated test account is not available yet.

## Stop and reset

Stop the stack with `Ctrl+C`, then:

```bash
docker compose down
```

To remove the local PostgreSQL data volume as well (destructive; this deletes locally stored projects):

```bash
docker compose down -v
```

## Troubleshooting

- If port 5173, 8000, or 5432 is already in use, stop the conflicting service or change the host-side port mapping in `docker-compose.yml`.
- If frontend dependencies change, rebuild with `docker compose build frontend`.
- If backend dependencies or the Dockerfile change, rebuild with `docker compose build backend`.
- Check service output with `docker compose logs -f frontend backend db`.
- If migrations fail, inspect the backend logs before resetting the database. Do not use `docker compose down -v` unless you intend to delete local project data.

## Current limitations

M0.2 is a development vertical slice, not production authentication. The app uses one configured local user. Invitation records are pending placeholders; no email is sent and no recipient can accept yet. Public/unlisted discovery, role administration, account registration, authentication, and invitation acceptance are not implemented.
