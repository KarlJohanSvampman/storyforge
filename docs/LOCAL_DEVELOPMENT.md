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
