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

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

The frontend uses the Vite development server. Requests to `/api` are proxied to the backend container, so browser code can call the API using relative paths.

Stop the stack with `Ctrl+C`, then:

```bash
docker compose down
```

To remove the local PostgreSQL data volume as well (destructive):

```bash
docker compose down -v
```

## Troubleshooting

- If port 5173, 8000, or 5432 is already in use, stop the conflicting service or change the host-side port mapping in `docker-compose.yml`.
- If frontend dependencies change, rebuild with `docker compose build frontend`.
- If backend dependencies change, rebuild with `docker compose build backend`.
- Check service output with `docker compose logs -f frontend backend db`.

## Current limitations

This is the M0.1 bootstrap. The database container is provisioned, but the API does not yet read or write database records. Authentication, project creation, collaboration, and AI integration are future milestones.
