# Roadmap

## Working method

Work in small, demonstrable increments. Each milestone should produce something runnable and testable. Prefer a vertical slice over broad scaffolding.

## M0 — Collaborative storytelling

### M0.1 — Runnable skeleton
- [ ] React + TypeScript frontend starts locally.
- [ ] FastAPI backend starts locally.
- [ ] Frontend can call a health endpoint.
- [ ] Docker Compose runs the stack.
- [ ] README contains exact setup instructions.

### M0.2 — Projects
- [ ] Create and list projects.
- [ ] View project details.
- [ ] Define basic project membership and roles.
- [ ] Persist data in PostgreSQL.

### M0.3 — Contributions
- [ ] Participants submit independent story contributions.
- [ ] Contributions display author and creation time.
- [ ] Original contributions remain immutable or version-preserved.
- [ ] Project participants can read contributions according to permissions.

### M0.4 — Discussion and suggestions
- [ ] Add comments to contributions and drafts.
- [ ] Submit a suggestion referencing a target.
- [ ] Accept, reject, or defer a suggestion.
- [ ] Preserve discussion history.

### M0.5 — Draft compilation and AI seam
- [ ] Create a combined narrative draft from selected contributions.
- [ ] Record which contributions informed the draft.
- [ ] Provide an AI provider interface, initially with a deterministic/mock implementation.
- [ ] Store AI output as an unapproved proposal.
- [ ] Allow a participant to edit and submit a revised proposal.

### M0.6 — Approval and phase progression
- [ ] Configure a simple project approval rule.
- [ ] Record votes and approval decisions.
- [ ] Approve a specific immutable narrative version.
- [ ] Move the project to the storyboard phase only after approval.
- [ ] Show phase and decision history.

## Definition of done for M0

A small group can create a project, submit individual contributions, discuss and suggest changes, produce a combined draft, approve a specific version, and see the project move to the storyboard phase. The workflow must preserve authorship and history.

## Deferred

Do not implement webcam tracking, facial capture, WebXR, character rigs, virtual cameras, editing, scoring, or project forking during M0. Keep their future requirements in mind without building speculative infrastructure.
