# Production, Actor, and Performance Architecture

> Status: architecture baseline. SceneRun/CastMemberInstance runtime, controller authority and possession leases, structured takes, a Three.js set viewport, and JSON edit-decision-list assembly are now implemented in the M2.1–M3 development slice. See `SCENE_RUNTIME_AND_EDITORIAL_MODEL.md` for the executable contracts and current boundaries.

## 1. Delivery boundary

StoryForge is being delivered incrementally. Collaborative storytelling and approval remain the first implementation target. Actor runtime, performance commands, AI acting, and the Director's Studio belong to the later production workspace. Do not build a disconnected Studio mock or add runtime/3D infrastructure before the earlier milestones provide the project, membership, and approved-narrative foundations.

The production workspace must reference an approved narrative version, while keeping production interpretation independently editable.

## 2. Core domain distinction

Keep these concepts separate:

- **Actor:** a persistent performer in the talent domain. An actor can exist without being attached to a production and may be reused across productions.
- **Character:** a fictional person belonging to a production's story. Personality, motivations, relationships, knowledge, and story identity belong here.
- **CastingAssignment:** a production-scoped relationship that assigns an actor to portray a character. It is the stable bridge between production data and the talent domain.
- **Controller:** the user, AI agent, script engine, or system process currently authorized to determine an actor's performance. Control is not actor ownership and is not part of the actor's identity.
- **CastMemberInstance:** a runtime instance of a casting assignment inside a particular scene run.

A character can have one active casting assignment at a time in a given production. Historical assignments should be retained. An actor may be reused across productions and may portray multiple characters in one production where the production permits it. Any schedule or simultaneous-instance restrictions are policy, not identity constraints.

## Actor profiles and casting foundation

The M2 actor foundation separates three identities:

- An Actor is a persistent performer profile owned by a user and reusable across productions.
- A Character remains a fictional person owned by a project story bible.
- A CastingAssignment links one Actor to one Character within one project. Recasting ends the previous active assignment instead of deleting history.

A project has performance defaults for controller type and control mode. Each casting assignment can override those defaults. Controller types (user, ai_agent, script_engine, system) are independent of control modes (direct, command, assisted, autonomous, scripted). Human controllers must be active project members. Director remains a project permission/role and is not a controller type. Actor ownership is not changed by casting.

Project settings govern whether one actor may portray multiple characters and whether a character may be recast. The current API permits a user to cast only actor profiles they own; cross-user talent permissions and revocable manager relationships are a later talent-domain milestone. Runtime possession, authority epochs, scene runs, and cast-member instances are deliberately not included in this persistence foundation.

## 3. Production and runtime entities

### Persistent entities

- `Production`
- `Character`
- `Actor` (owned by the talent domain)
- `CastingAssignment`
- `Scene`
- `SceneMark`
- `ProjectPerformanceSettings`
- `CharacterPerformanceProfile`
- `AnimationDefinition` / asset references

### Runtime entities

- `SceneRun`: one execution or rehearsal of a scene. A scene can have multiple independent runs or takes.
- `CastMemberInstance`: the runtime representation of one casting assignment in one SceneRun.
- `ControllerAssignment`: the effective or configured controller for an instance, including its control mode and authority epoch.
- `PossessionLease`: temporary direct control by a player, with expiry and a fencing token.
- `PerformanceCommand` and `PerformanceExecution`: requested action and its execution lifecycle.
- `PerformanceSequence` / `PerformanceBeat`: coordinated actions, including sequential and parallel groups.
- `AIPerformanceContext`: temporary context for an AI-controlled character; it is not stored on the persistent Actor record.

A SceneRun must be isolated from every other run, even when the same scene and casting assignments are used. Runtime state from one take must not leak into another.

## 4. Control model

Controller identity and control mode are separate.

Controller types:

- `user`
- `ai_agent`
- `script_engine`
- `system`

Control modes:

- `direct`: low-latency player input
- `command`: semantic instructions such as move, look, gesture, or interact
- `assisted`: player input combined with permitted AI assistance
- `autonomous`: AI chooses actions within production constraints
- `scripted`: a predefined performance sequence drives the actor

Director is a production role/permission bundle, not a controller type. A director can issue commands or request possession without becoming the permanent controller.

Configuration is resolved from platform defaults, production settings, casting-assignment overrides, and scene-level settings. Temporary possession is an overlay on this policy: releasing or expiring possession restores the previously resolved controller, unless the policy changed while possession was active.

Every authority change increments a monotonic `control_epoch`. Commands and direct-input packets must carry the current epoch and, when applicable, the active possession lease/fencing token. Stale packets from a previous controller are rejected. A possession lease must expire or be released on disconnect, scene end, or revocation.

## 5. Casting and runtime lifecycle

1. Create a Character in a Production.
2. Select or create an Actor in the talent domain.
3. Create a CastingAssignment linking the Actor and Character.
4. Start a SceneRun.
5. Create one CastMemberInstance for each participating casting assignment.
6. Resolve controller policy and create runtime controller assignments.
7. Execute performance commands and direct-input streams against the CastMemberInstance, never against the persistent Actor or Character record.
8. End the SceneRun and close runtime instances without deleting persistent actors, characters, scenes, or casting history.

The persistence layer stores canonical production and casting records plus important runtime checkpoints. High-frequency transforms, animation frames, and direct-input samples belong in the runtime/streaming layer, not as one relational-database write per frame.

## 6. Common performance interface

Player, director, AI, and script controllers use the same semantic command contract. The command identifies the `scene_run_id` and `cast_member_instance_id`, issuer, authority epoch, command type, typed payload, priority, execution policy, idempotency key, and correlation ID.

Initial semantic actions:

- Movement: `move_to`, `approach`, `retreat`, `follow`, `turn_to`, `stop`
- Gaze: `look_at`, `look_away`, `look_direction`, `face_target`
- Gestures: `play_gesture`, `wave`, `nod`, `shake_head`, `shrug`, `point_at`, `cross_arms`
- Expressions: `set_expression`, `clear_expression`
- Interaction: `pick_up`, `put_down`, `open`, `close`, `sit_down`, `stand_up`, `interact_with`

Direct control is intentionally not represented as a high-volume sequence of semantic commands. It uses a separate low-latency input stream, validated against the same current authority epoch. Both paths update the same authoritative runtime state.

## 7. Execution, channels, and events

Commands are validated, authorized, queued or rejected, then executed by the appropriate subsystem. Command lifecycle states include `received`, `validating`, `accepted`, `queued`, `executing`, `completed`, `failed`, `interrupted`, `cancelled`, and `expired`.

Each CastMemberInstance has an independent scheduler. Actions reserve resources/channels rather than claiming one global animation slot. Initial channels include locomotion, body pose, upper body, left hand, right hand, head, gaze, facial, voice, and interaction. An animation definition declares the channels/body parts it uses, its blending behaviour, requirements, and interruption policy. Conflicting actions are arbitrated only on overlapping resources where possible; unrelated actions (for example, locomotion and facial expression) may run concurrently.

Subsystems emit lifecycle events when durable state transitions occur. Event delivery is a notification mechanism, not the source of truth. Consumers can reload canonical state after reconnect. Persist important events through a transactional outbox or equivalent reliability mechanism when the event bus is introduced.

## 8. AI acting

AI receives a bounded context assembled by backend services: character profile, current scene, relevant dialogue, relationships/knowledge, visible and audible events, physical state, director instructions, available actions, and production constraints. The AI returns a typed performance plan or semantic action proposal. The backend validates all actor IDs, marks, targets, action names, permissions, and limits before translating the plan into ordinary PerformanceCommands.

AI must never directly set authoritative transforms, skeleton poses, animation frames, controller assignments, approvals, or arbitrary database fields. It cannot invent valid asset IDs or bypass the command authorization layer.

Autonomy is configurable by actor/character and scene. Dialogue generation, emotional interpretation, gestures, autonomous movement, reactions, and improvisation are independent capabilities. A character may be human-controlled for movement while AI assists with gaze or facial reactions, subject to the production's settings.

Autonomous reactions are driven by relevant perception events. Event delivery is filtered by what the character can plausibly see, hear, or otherwise know; actors must not receive global scene knowledge automatically. Emotional state, facial expression, and outward behaviour are separate concepts.

## 9. Director's Studio

The future Director's Studio is a configurable workspace with:

- a Three.js scene viewport
- cast panel and actor selection
- actor inspector and controller/possession controls
- scene marks and blocking editor
- natural-language director command panel with preview/approve/immediate policies
- performance monitor and timeline
- take/rehearsal controls

Selection is not possession. Selecting an actor inspects or targets them; possession grants temporary direct control. Viewport dragging in edit mode changes authored blocking; it must not silently override a live controller during rehearsal or recording.

The Studio should use the production and performance APIs as the source of truth. Rendering state is client-side, but clients cannot directly write authoritative runtime transforms or bypass permissions.

## 10. Takes and provenance

A SceneRun represents a rehearsal or take. Preserve the director's original instruction, AI interpretation, validated plan, issued commands, controller changes, direct-input recording where enabled, selected animation assets, dialogue/audio references, timing, and scene events. Keep this structured performance source separate from the rendered video and from the final editing timeline.

Recording must identify the versions of assets, rigs, animation definitions, and execution logic needed for faithful replay. Exact deterministic replay may not be possible for all physics- or AI-driven performances; preserve generated decisions and input data so the system can reproduce or approximate the take and disclose where it cannot guarantee bit-identical output.

## 11. Delivery order

Do not skip the storytelling foundation to build the Studio first.

1. M0: collaborative storytelling, immutable contributions, draft provenance, discussion, suggestions, approval, and phase history.
2. M1: storyboard, scenes, basic character records, locations, sets, and props.
3. M2 foundation: actors, characters, casting assignments, controller policies, SceneRuns, CastMemberInstances, possession, and event contracts.
4. M2 performance: semantic commands, per-instance scheduler, navigation, animation channels, scene marks, and basic gestures.
5. M2 Studio: cast panel, Three.js viewport, inspector, blocking tools, command preview/execution, and switching.
6. Later: AI performance planning, perception/reactions, dialogue integration, collaborative control, takes, timeline, and recording refinement.

Keep each stage as a runnable vertical slice. Avoid empty abstractions for future systems until a concrete milestone needs them.
