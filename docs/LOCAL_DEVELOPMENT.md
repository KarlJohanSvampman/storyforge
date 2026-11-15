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


## M0.6 approval and phase progression

The project approval panel appears below the combined narrative draft. A project defaults to **Owner approval** until the owner saves a different rule.

- **Owner approval:** only the owner votes; one approve or reject vote meets the threshold.
- **Majority:** active owners, editors, and contributors vote. More than half must agree. Viewers and pending invitations do not count.
- The first vote opens a ballot and freezes its eligible voter list, roles, rule mode, and threshold for that exact version. Later project membership changes do not silently recalculate an open ballot.
- A vote may be changed before a final decision. Every vote event is retained; only the latest vote by each eligible member counts.
- The owner finalizes the decision after the approve or reject threshold is reached. The decision is attached to the exact draft version.
- Rejection leaves the project in its current phase. The group can create another draft version and vote on it.
- Approval moves the project to **storyboard** and adds a phase-history record. Further narrative compilation, draft editing, voting, and approval-rule changes are then locked.

The local development identity is one fixed project owner. You can exercise owner-only approval and the majority rule with that single active creative member (the required majority is one). Real multi-person tally verification requires authentication and accepted invitations, which are not implemented yet.

### M0.6 API endpoints

- `GET /api/projects/{project_id}/approval` — approval rule, per-version vote tallies/history, decisions, and project phase history.
- `PUT /api/projects/{project_id}/approval-rule` — owner-only rule configuration; body: `{"mode":"owner_only"}` or `{"mode":"majority"}`. Locked after voting starts.
- `POST /api/projects/{project_id}/draft/{draft_id}/versions/{version_id}/votes` — cast or change the current user's vote; body: `{"choice":"approve","note":""}` or `{"choice":"reject","note":""}`.
- `POST /api/projects/{project_id}/draft/{draft_id}/versions/{version_id}/decision` — owner finalizes the threshold result; body: `{"note":""}`. Returns HTTP 409 if neither side has met the threshold.
- A successful approval changes `Project.current_phase` to `storyboard` and creates a project phase transition in the same database transaction.

### M0.6 verification checklist

1. Open a project with a draft and confirm the default is owner approval.
2. As owner, switch the rule to majority before any votes. Confirm a non-owner cannot change the rule.
3. Cast an approve vote, then change it to reject. Confirm both events remain in history and only the latest vote is counted. Confirm the ballot preserves the rule mode, electorate and threshold captured when the first vote was cast.
4. Attempt to finalize with no threshold reached; confirm HTTP 409 and no phase change.
5. Reach the reject threshold and finalize. Confirm the version is marked rejected in approval history and the project phase is unchanged.
6. Create a new immutable proposal version, vote to approve it, and finalize approval as owner.
7. Confirm the project moves to `storyboard`, the approved version and decision are identified, and the phase-history panel records the transition.
8. Attempt to compile, manually revise, vote, or change the rule after approval. Confirm the API rejects these operations.
9. Restart Docker Compose and confirm votes, decisions, rule, and phase history persist.

## M1.1 storyboard and creative assets

After a narrative is approved and the project reaches the **storyboard** phase, open the project again. The Storyboard section offers an **Initialize storyboard** action. Initialization is anchored to the exact narrative version recorded by the approved phase transition; it does not use whichever draft happens to be newest.

The storyboard workspace supports:

- A project character directory with story description, visual description, personality notes, and active/archived status.
- A project location directory with environment type, time period, description, visual notes, and active/archived status.
- Ordered scenes with summary, production requirements, estimated duration in seconds, one primary location, and participating characters.
- Moving scenes up and down. The reorder API requires the complete current scene ID list exactly once.
- Exact links from a scene to a passage in the approved narrative. Copy the exact passage from the expandable approved-narrative panel and paste it into the scene's link form. If the same text occurs more than once, set the 1-based occurrence number. The API resolves and stores the exact excerpt plus source offsets; it rejects text not present in the approved version.
- Working script material per scene. Saving always creates a new immutable script revision. When editing an existing script, the client includes the version it started from; a stale save returns HTTP 409 rather than overwriting a newer revision.

Character and location records are story-bible entries, not actor profiles, casting records, built 3D sets, or props. Script revisions are working production material and do not alter the approved story. Owners, editors, and contributors may edit the storyboard while the project is in the storyboard phase; viewers can read it. The API blocks writes after the project advances to another phase.

### M1.1 API endpoints

- `GET /api/projects/{project_id}/storyboard` — get the storyboard and its approved narrative source, or `null` when it has not been initialized.
- `POST /api/projects/{project_id}/storyboard` — initialize the storyboard from the approved narrative transition; repeat calls return the existing storyboard.
- `POST /api/projects/{project_id}/storyboard/characters` and `PATCH .../characters/{character_id}` — create/update project character records.
- `POST /api/projects/{project_id}/storyboard/locations` and `PATCH .../locations/{location_id}` — create/update project location records.
- `POST /api/projects/{project_id}/storyboard/scenes` and `PATCH .../scenes/{scene_id}` — create/update scene breakdown and assignments.
- `PUT /api/projects/{project_id}/storyboard/scenes/reorder` — set the complete scene order; body: `{"scene_ids":["..."]}`.
- `POST /api/projects/{project_id}/storyboard/scenes/{scene_id}/passages` — link exact source text; body: `{"passage_text":"exact copied passage","occurrence":1}`.
- `POST /api/projects/{project_id}/storyboard/scenes/{scene_id}/script` — append a script revision; body: `{"base_version_id":null,"content":"..."}` for the first revision, then send the current revision ID on subsequent saves.

### M1.1 verification checklist

1. Complete M0.6 approval and confirm the project is in the storyboard phase.
2. Initialize the storyboard. Confirm its narrative title/version and complete source text match the exact approved version recorded in phase history.
3. Repeat initialization. Confirm the same storyboard is returned rather than creating a second one.
4. Create several characters and locations; archive one of each through the API and confirm their existing scene relationships remain readable.
5. Create at least three scenes with different summaries, requirements, durations, locations, and character assignments.
6. Reorder scenes several times. Confirm positions are contiguous and stable after refreshing the project.
7. Copy an exact paragraph from the approved narrative and link it to a scene. Confirm the stored excerpt and offsets are correct. Try text that is not present and confirm HTTP 422. Try a repeated excerpt with occurrence 2 and confirm the second occurrence is selected.
8. Save a first script revision, then save a second revision. Confirm both remain in history and the second references the first as its parent. Submit a stale base version and confirm HTTP 409.
9. Confirm a viewer cannot create/update storyboard data. Confirm a write attempt after the project leaves the storyboard phase returns HTTP 409.
10. Restart Docker Compose and confirm scenes, assets, source references, and script revisions persist.

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
