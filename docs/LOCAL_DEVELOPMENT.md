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

Each storyboard is unique to the pair of project and approved narrative version. Repeating initialization for the same approved version returns the existing storyboard. If a future phase-management workflow sends a project back through approval with a different narrative version, a separate storyboard can be created while the earlier interpretation remains stored. M0.6 currently implements the initial advance into storyboarding; returning to earlier phases is a later workflow capability.

The storyboard workspace supports:

- A project character directory with story description, visual description, personality notes, and active/archived status.
- A project location directory with environment type, time period, description, visual notes, and active/archived status.
- Ordered scenes with summary, production requirements, estimated duration in seconds, one primary location, and participating characters.
- Moving scenes up and down. The reorder API requires the complete current scene ID list exactly once.
- Exact links from a scene to a passage in the approved narrative. Copy the exact passage from the expandable approved-narrative panel and paste it into the scene's link form. If the same text occurs more than once, set the 1-based occurrence number. The API resolves and stores the exact excerpt plus source offsets; it rejects text not present in the approved version.
- Working script material per scene. Saving always creates a new immutable script revision. When editing an existing script, the client includes the version it started from; a stale save returns HTTP 409 rather than overwriting a newer revision.

Character and location records are story-bible entries, not actor profiles, casting records, built 3D sets, or props. Script revisions are working production material and do not alter the approved story. Owners, editors, and contributors may edit the storyboard while the project is in the storyboard phase; viewers can read it. The API blocks writes after the project advances to another phase.

### M1.1 API endpoints

- `GET /api/projects/{project_id}/storyboard` — get the most recently initialized storyboard and its approved narrative source, or `null` when none has been initialized.
- `POST /api/projects/{project_id}/storyboard` — initialize from the latest approved narrative transition; repeat calls for the same narrative version return the existing storyboard. A different approved narrative version can have its own storyboard history.
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

## M1.2 structured screenplay authoring

Open a scene in the storyboard and select **Write screenplay** or **Edit as structured screenplay**. The editor supports ordered blocks:

- **Action:** visible action and scene description.
- **Dialogue:** spoken words attributed to a story character.
- **Parenthetical:** delivery or performance note, optionally associated with a character.
- **Transition:** a screenplay transition such as `CUT TO:`.
- **Production note:** a non-dialogue instruction for production planning.

Add blocks, change their type, move them up/down, or remove them. Saving creates a new immutable script revision; it does not modify the previous revision. The generated screenplay preview is a deterministic rendering of the saved blocks. Dialogue must use a character already assigned to the scene. A speaker's name is snapshotted in the script element, so later character renaming does not silently rewrite old script versions.

M1.1 plain-text script revisions remain readable. Opening a legacy text revision in the structured editor imports it as one initial **Action** block. Saving creates a new structured revision and leaves the legacy revision intact.

### M1.2 API contract

The existing script endpoint accepts either legacy text or a structured list, but not both:

- Legacy payload: `{"base_version_id":null,"content":"Plain-text script"}`.
- Structured payload:
```json
{
  "base_version_id": null,
  "elements": [
    {"element_type": "action", "content": "A door opens.", "character_id": null},
    {"element_type": "dialogue", "content": "You're late.", "character_id": "SCENE_CHARACTER_UUID"},
    {"element_type": "parenthetical", "content": "quietly", "character_id": "SCENE_CHARACTER_UUID"},
    {"element_type": "transition", "content": "CUT TO:", "character_id": null},
    {"element_type": "production_note", "content": "A practical light flickers.", "character_id": null}
  ]
}
```

Supported element types are `action`, `dialogue`, `parenthetical`, `transition`, and `production_note`. Each element stores its order and text. Dialogue requires a character. Any selected character must be active and already assigned to the scene; a character from another project, an archived character, or an unassigned character returns HTTP 422. A character may speak multiple times in one script. The API response includes both the generated `content` and the structured `elements` for each script version.

A non-null `base_version_id` must match the latest script version. Stale updates return HTTP 409. The first revision uses `base_version_id: null`.

### M1.2 verification checklist

1. Create a scene and assign at least two active story characters to it.
2. Add action, dialogue, parenthetical, transition, and production-note blocks. Use the same character for multiple dialogue lines.
3. Move blocks into a different order, edit content, and save. Confirm the rendered script follows the block order and the API response contains the same ordered typed blocks.
4. Confirm dialogue requires a speaker. Try an unassigned character, an archived character, and a character from another project; confirm the API returns HTTP 422.
5. Create a second revision. Confirm the first remains unchanged and the second points to it as parent. Attempt a stale base version and confirm HTTP 409.
6. Open a scene whose latest script is a legacy plain-text M1.1 revision. Confirm it appears as one Action block. Save it and confirm the new version has structured elements while the legacy version remains unchanged.
7. Confirm a viewer cannot create script revisions and a script cannot be written after the project leaves the storyboard phase.
8. Restart Docker Compose and confirm structured elements, character name snapshots, and script revision history persist.

## M1.3 project formats and TV-series authoring

New projects can be created with two independent selectors:

- **Production format:** Movie or TV series.
- **Content category:** Fiction or Documentary.

Genre / subject remains free-form descriptive metadata. Examples include drama, fantasy, history, nature, crime, or science. It does not determine whether a project is a movie, series, fiction, or documentary. Existing database projects migrate with Movie + Fiction defaults.

For a movie, scenes remain directly under the storyboard and use one project-level scene sequence. For a TV series, create seasons and then episodes. Each episode owns its own ordered scenes and screenplay revisions. Scenes cannot be created for a series without selecting an active episode.

Seasons have a title, description, and overarching story arc. Episodes have a title, logline, synopsis, and optional estimated runtime in seconds. Seasons and episodes can be archived and restored; archiving does not delete episodes, scenes, script revisions, or their history. New scenes cannot be attached to archived episodes or episodes in archived seasons.

The API prevents changing a project's production format after its first storyboard has been initialized. This avoids changing a movie's flat scene structure into a series hierarchy (or vice versa) after scene data exists. Content category remains an editable project classification.

### M1.3 API endpoints

- Project create/read/update payloads now include format (movie or tv_series) and category (fiction or documentary).
- `POST /api/projects/{project_id}/storyboard/seasons` — create a season with season_number, title, description, and story_arc.
- `PATCH /api/projects/{project_id}/storyboard/seasons/{season_id}` — update a season or archive/restore it with status active/archived.
- `POST /api/projects/{project_id}/storyboard/seasons/{season_id}/episodes` — create an episode with episode_number, title, logline, synopsis, and optional estimated_duration_seconds.
- `PATCH /api/projects/{project_id}/storyboard/episodes/{episode_id}` — update or archive/restore an episode.
- `POST /api/projects/{project_id}/storyboard/scenes` and `PATCH .../scenes/{scene_id}` accept episode_id. Movie scenes use null; TV-series scenes require an episode in the same storyboard.
- `PUT /api/projects/{project_id}/storyboard/scenes/reorder` accepts episode_id plus the complete ordered scene_ids list. For a series, reorder one episode at a time. For a movie, episode_id is null. Every scene in the selected sequence must be included exactly once.

### M1.3 verification checklist

1. Create a movie-fiction project and a movie-documentary project. Confirm each displays both selected dimensions independently.
2. Create a TV-series-fiction project and a TV-series-documentary project. Confirm either category can use the series format.
3. Confirm projects created before this migration are returned as movie + fiction.
4. Approve a narrative and initialize a TV-series storyboard. Create two seasons and multiple episodes per season, including their descriptions, arcs, loglines, synopses, and runtimes.
5. Create scenes in two different episodes. Confirm each episode's scene order begins at 1 and ordering/reordering in one episode does not affect another episode.
6. Move a scene to a different active episode. Confirm it receives the next scene order in the destination episode and its screenplay history remains attached.
7. Try creating a series scene without an episode, with an episode from another storyboard, or under an archived episode/season. Confirm validation rejects each request.
8. Archive and restore a season and episode. Confirm scene/script records remain visible and preserved, and new scenes are blocked while the containing season/episode is archived.
9. Confirm movie scene creation/reordering still works with a null episode_id, and that a movie cannot be assigned a TV episode.
10. Attempt to change format after storyboard initialization; confirm HTTP 409. Confirm category can still be changed.
11. Confirm viewers cannot write seasons, episodes or scenes, and all write actions are blocked after the project leaves the storyboard phase.
12. Restart Docker Compose and confirm formats, categories, seasons, episodes, scene assignments, and screenplay revisions persist.

## M1.4 documentary research and claim-level fact-checking

The documentary workspace appears on a project detail page when the project's category is **Documentary**. It is project-level, so researchers can begin before a storyboard exists. Both movie-documentaries and documentary series use the same register.

The source register captures source type, title, creator/author, publisher/institution, publication date, URL, citation text, notes, and an access timestamp. Researchers may enter the time they accessed the source; if left blank, the server records when the source entry was created. It is a bibliographic register, not a document downloader: source content must currently be reviewed externally and excerpts entered manually.

Claims are discrete factual statements with an origin of **Human-authored** or **AI-assisted**. Both begin unreviewed. Each claim can be linked to a source using an evidence relationship:
- **Supports:** the source provides evidence in favour of the statement.
- **Challenges:** the source provides evidence against the statement.
- **Context:** the source provides relevant context without being marked as direct support or contradiction.

Each evidence link stores an exact excerpt, a page/section/table/timecode locator, and researcher notes. A single source can currently be linked once to a given claim. Evidence links are append-only. Claims are not edited in place in this slice; archive a claim and create a replacement if its wording needs to materially change.

A human project member records a fact-check result and rationale. The API enforces:
- **Supported:** at least one active linked source must be marked Supports.
- **Contested:** active evidence must include both Supports and Challenges.
- **Not supported:** at least one active linked source must be marked Challenges.
- **Insufficient evidence:** can be recorded even when no suitable source is yet linked.

Every review stores the reviewer, result, rationale, and a snapshot of the active source metadata and evidence excerpts available at that moment. Adding evidence or changing/archiving a cited source changes a previously reviewed claim to **Needs review**; prior review history remains intact. An AI-assisted claim cannot mark itself supported. Only a signed-in project member can submit a human review.

### M1.4 API endpoints

- `GET /api/projects/{project_id}/documentary` — retrieve the complete source register, claim ledger, evidence links, and review history.
- `POST /api/projects/{project_id}/documentary/sources` — add a source.
- `PATCH /api/projects/{project_id}/documentary/sources/{source_id}` — update source metadata or archive/restore it. This invalidates any current claim review that relied on the source.
- `POST /api/projects/{project_id}/documentary/claims` — create a human-authored or AI-assisted factual claim.
- `PATCH /api/projects/{project_id}/documentary/claims/{claim_id}` — archive/restore a claim; claim statement text is immutable in this slice.
- `POST /api/projects/{project_id}/documentary/claims/{claim_id}/evidence` — link an active source, evidence relationship, exact excerpt, locator, and notes. A source can be linked once per claim.
- `POST /api/projects/{project_id}/documentary/claims/{claim_id}/reviews` — append a human fact-check result and evidence snapshot.

All active project members can read. Owners, editors, and contributors can write. Viewers are read-only. Published projects are read-only. The API returns HTTP 409 when a non-documentary project accesses this workflow. Source URLs must use http:// or https://.

### M1.4 verification checklist

1. Create a documentary movie and a documentary TV series. Confirm the research workspace appears in both without requiring storyboard initialization.
2. Confirm fiction projects do not expose or access the documentary API (HTTP 409).
3. Add sources of several types, including an article, an academic paper, an official record, an interview, and an archival record. Confirm metadata, URL, citation, notes, creation time, and accessed time persist.
4. Submit a URL without http:// or https:// and confirm the API rejects it.
5. Create human-authored and AI-assisted claims. Confirm both begin with Unreviewed status and the origin label remains visible.
6. Try Supported without a supporting source; confirm HTTP 422. Link a source marked Supports and record the decision.
7. Try Contested with only supporting evidence; confirm HTTP 422. Add a Challenges source and confirm the result can now be recorded.
8. Try Not supported without a Challenges source; confirm HTTP 422. Confirm Insufficient evidence can be recorded with a rationale even when no evidence exists.
9. Confirm each review stores the reviewer, rationale, and evidence snapshot. Add more evidence and confirm the claim changes to Needs review while its earlier decision and snapshot remain in history.
10. Change or archive a cited source and confirm every claim that used it moves to Needs review. Confirm archived sources cannot be added as new evidence until restored.
11. Archive a claim and confirm it cannot receive evidence or a review; restore it and confirm its prior evidence and review history are still present.
12. Confirm viewers can read but cannot create sources/claims/evidence/reviews. Confirm writes are blocked after publication.
13. Restart Docker Compose and confirm sources, claims, evidence links, review results, and JSON evidence snapshots persist.

Interview releases/subject consent, archival-media rights and licensing, file uploads, automated source retrieval, and claim links into scenes/scripts are not implemented in this slice. These are tracked separately in M1.5. A source record or human fact-check decision is not a legal rights clearance and does not guarantee that a source is accurate; reviewers should document limitations and uncertainty.

## M1.5 reusable story-bible management

The character and location directories are project-level story-bible records. They are not owned by one individual storyboard interpretation, so later storyboard versions for the same project continue to use the same character and location identities.

Owners, editors, and contributors can edit profile details or archive/restore records while the project remains in the storyboard phase. Viewers and projects outside that phase are read-only.

Character profiles support name, story description, visual description, and personality notes. Location profiles support name, environment type, time period, description, and visual notes. Existing records are updated through the existing PATCH endpoints:

- `PATCH /api/projects/{project_id}/storyboard/characters/{character_id}`
- `PATCH /api/projects/{project_id}/storyboard/locations/{location_id}`

Archiving preserves all existing scene participation, location references, and screenplay revisions. Archived items remain visible in a collapsible directory section and can be restored. New scene assignments may only use active characters and locations. Existing scenes may retain their archived references while other scene details are edited; users can explicitly remove an archived character or location reference. Once removed, an archived item cannot be assigned again until restored.

Renaming a character updates the current directory and scene-participant labels. Saved screenplay text and structured screenplay character-name snapshots do not change. New dialogue must use an active character already assigned to the scene. Restore an archived character before creating new dialogue for that role.

### M1.5 verification checklist

1. Initialize a storyboard and create at least two characters and two locations with non-empty profile fields.
2. Edit each character field and save. Confirm the directory reflects the new profile after a reload.
3. Edit each location field and save. Confirm scenes that reference the location show the updated name.
4. Create a scene assigned to both characters and one location. Save a structured screenplay with dialogue attributed to a character.
5. Rename that character. Confirm current scene labels use the new name while existing screenplay content and the structured element's character-name snapshot remain unchanged.
6. Archive a character assigned to an existing scene. Confirm the participant remains visible as archived and the existing screenplay history remains readable.
7. Edit an unrelated field on the same scene while retaining the archived character. Confirm the update succeeds. Remove the archived character from the scene and save; confirm a later attempt to reassign it fails until the character is restored.
8. Try creating a new scene with an archived character and confirm HTTP 422. Try adding new dialogue for an archived character and confirm it is unavailable in the UI and rejected by the API.
9. Archive a location used by a scene. Confirm the scene keeps the archived location label. Edit another scene field while keeping the location unchanged; confirm the update succeeds. Try assigning that archived location to a different scene and confirm HTTP 422.
10. Remove an archived location from its existing scene, then confirm it cannot be selected for a new scene until restored.
11. Restore archived characters and locations. Confirm they return to the active directory and become selectable for new scene assignments and dialogue.
12. Confirm viewers cannot edit profiles or archive/restore records, and confirm all writes are blocked after the project leaves the storyboard phase.
13. Create a later storyboard interpretation for the same project if the approval flow permits it. Confirm the same project-level story-bible identities are returned and remain reusable.
14. Restart Docker Compose and confirm profile updates, archived statuses, scene references, and screenplay history persist.


## M1.6 documentary interviews, consent, media and claim placement

M1.6 adds a second workspace alongside the existing M1.4 source/claim register. Both are shown on documentary movie and documentary-series projects, including before a storyboard exists. The production overview is available from:

- `GET /api/projects/{project_id}/documentary/production`

Interview directory:
- `POST /api/projects/{project_id}/documentary/interview-subjects` — add a subject with a named, pseudonym, or anonymous identity mode.
- `PATCH /api/projects/{project_id}/documentary/interview-subjects/{subject_id}` — edit subject details or archive/restore the record.
- `POST /api/projects/{project_id}/documentary/interview-sessions` — record the subject, date/time, interviewer, format, location/platform, and transcript/session notes.
- `PATCH /api/projects/{project_id}/documentary/interview-sessions/{session_id}` — update notes/format or archive/restore the session.

Consent:
- `POST /api/projects/{project_id}/documentary/releases` — create a draft or signed release. Signed records require an explicit `signed_at` timestamp. Each record stores the subject, optional session, project/production/release scope, consent wording, permitted uses, optional expiry, withdrawal terms, and optional private signed-document file.
- `POST /api/projects/{project_id}/documentary/releases/{release_id}/withdraw` — record a required reason and append a withdrawal event. The status becomes withdrawn; the prior record and event remain visible.
- Release creation and withdrawal are performed by project members, not by the interview subject through a verified identity/signature flow. A status of signed is a project-record assertion, not a cryptographic signature or legal certification.

Private media:
- `POST /api/projects/{project_id}/documentary/media` — multipart upload fields: `file`, `title`, `asset_type`, optional `source_id`, optional `interview_session_id`, optional `duration_seconds`.
- `GET /api/projects/{project_id}/documentary/media/{asset_id}/download` — membership-protected download; signed release documents are restricted to owners/editors.
- Each uploaded record stores original filename, detected-from-extension content type, byte size, SHA-256 digest and a private storage key. The storage key is not returned to the browser.
- Uploads are limited to 100 MiB. The current extension allowlist covers PDF, TXT/Markdown, CSV, JSON, DOCX/ODT, common MP3/WAV/M4A/MP4/MOV/WebM, and PNG/JPEG/TIFF files.
- Docker Compose mounts a named volume, `storyforge_documentary_media`, at `/app/storage/documentary`. Database backups alone do not include uploaded bytes; back up the database and media volume together. Removing the volume permanently removes those files.

Rights:
- `POST /api/projects/{project_id}/documentary/media/{asset_id}/rights` — create a new versioned rights/provenance record. The previous version is retained and marked superseded. Capture rights holder, basis, licence, territory, validity, permitted uses, attribution, and restrictions.
- A new rights record supersedes the earlier record. The current clearance check requires a current, effective, non-expired rights record whose permitted uses include the destination use (or `all`).
- If the asset is tied to an interview session, the usage check also requires a signed, non-expired project or production release for the same subject and destination use. A session-specific release applies only to that session; a project/production release without a session reference covers the subject's sessions.
- A release scoped to one future publication/release is recorded for reference but is not a general project/production permission.

Claim placements:
- `POST /api/projects/{project_id}/documentary/claims/{claim_id}/usages` — append a placement of a currently Supported claim into an outline, scene, exact screenplay revision, narration, lower-third or caption.
- A scene must belong to this project. A screenplay revision must belong to the selected scene. Existing usages are retained as append-only references.
- A claim with a later `needs_review`, contested, or otherwise non-supported current state is not eligible for new placements. Existing placement history remains, and the overview reports the claim's current review status.

All endpoints above require a documentary-category project. Read access requires project membership; writes require an owner, editor, or contributor and are blocked after publication. Viewers cannot write. A non-documentary project receives HTTP 409.

### M1.6 verification checklist

1. Create a documentary movie and documentary series; open both before and after storyboard initialization. Confirm the production workspace is present independently of the series hierarchy.
2. Create named, pseudonymous, and anonymous subjects. Confirm project members see the entered identity label and archive/restore preserves the directory.
3. Create multiple sessions for a subject with distinct dates, interviewers, formats, locations/platforms and notes. Confirm a session cannot be created for an archived subject and a session from another project is rejected.
4. Upload a transcript and an audio/video file linked to their session. Confirm metadata, byte size, SHA-256, file persistence after container restart, and private download access.
5. Try an unsupported extension, empty file, mismatched media type, and file larger than 100 MiB. Confirm upload validation rejects them and no partial file is exposed.
6. Upload a signed release document. Confirm a viewer cannot download it while an owner/editor can. Verify the file is still stored outside the public frontend tree.
7. Create a draft release and confirm it does not clear interview-use checks. Create a signed release with selected uses and an optional session scope; confirm a matching use is allowed only after rights clearance is also present.
8. Withdraw a signed release with a reason. Confirm an audit event is appended, the status becomes withdrawn, and future placements relying on that consent are rejected. Confirm a release for another session does not grant consent for this session.
9. Add media rights version 1, then a revised version. Confirm version 1 remains in history as superseded, the latest version is used, expiry blocks use, and missing/unknown rights do not clear production usage.
10. Create a claim with active source evidence, record a Supported human review, and link it to an outline. Confirm the exact claim ID and current review status are retained.
11. Try linking an unreviewed, contested, archived, or needs-review claim; confirm HTTP 409. For scene and screenplay placements, try a scene from another project and a script version from another scene; confirm rejection.
12. Confirm rights checks enforce the destination use, and interview-linked evidence requires a matching current signed release. Try research-only rights for a screenplay placement and confirm it is rejected.
13. Confirm viewers can read production metadata but cannot create subjects, sessions, releases, uploads, rights versions or claim placements. Confirm writes are blocked after publication and a fiction project cannot access these routes.
14. Restart Docker Compose. Confirm interview metadata, consent history, media metadata, rights versions and claim placements persist. Verify that the separately mounted media volume still contains the corresponding uploaded bytes.

Security and legal limitations: this initial local-storage slice does not scan for malware, inspect file contents, encrypt files at rest, use external object storage, implement participant identity verification or e-signature, auto-transcode media, or automatically apply withdrawal/takedown instructions to a future published release. The extension allowlist is not a malware safety guarantee. Do not deploy the current development authentication/storage setup as a public production service or treat a rights-basis label as legal advice.

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
