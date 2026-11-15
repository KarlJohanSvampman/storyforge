import { FormEvent, useEffect, useMemo, useState } from "react";
import { Activity, Camera, Check, ChevronDown, ChevronUp, CircleDot, Clapperboard, Download, Film, Lock, Pause, Play, Plus, Radio, Save, Square, UserRound, Video } from "lucide-react";
import ThreeSceneViewport from "./ThreeSceneViewport";

type SceneOption = { id: string; title: string; characters: Array<{ id: string; name: string }> };
type Member = { id: string; display_name: string | null; email: string | null; role: string; status: string };
type ControllerType = "user" | "ai_agent" | "script_engine" | "system";
type ControlMode = "direct" | "command" | "assisted" | "autonomous" | "scripted";
type CastMember = {
  id: string; actor_snapshot: { display_name?: string }; character_snapshot: { name?: string };
  controller_type: ControllerType; controller_user_id: string | null; control_mode: ControlMode;
  authority_epoch: number; state_snapshot: Record<string, unknown>;
};
type SceneRun = {
  id: string; scene_id: string; run_number: number; status: string; scene_snapshot: Record<string, any>;
  cast_members: CastMember[]; created_at: string; started_at: string | null; ended_at: string | null;
};
type TakeEvent = { id: string; event_order: number; timestamp_ms: number; event_type: string; cast_member_instance_id: string | null; authority_epoch: number | null; payload: Record<string, unknown> };
type Take = { id: string; scene_run_id: string; take_number: number; status: string; duration_ms: number; event_count: number; state_snapshot: Record<string, unknown>; events: TakeEvent[] };
type EditItem = { id: string; take_id: string; scene_id: string; item_order: number; in_ms: number; out_ms: number; transition: string; title_overlay: string; effects: Record<string, unknown>; audio_cue: string };
type EditSequence = { id: string; name: string; status: string; revision_number: number; items: EditItem[] };
type Lease = { id: string; lease_token: string; expires_at: string; authority_epoch: number };
type Props = { projectId: string; phase: string; scenes: SceneOption[]; members: Member[]; currentUserId: string | null; canManage: boolean };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const controllerLabels: Record<ControllerType, string> = { user: "Human", ai_agent: "AI agent", script_engine: "Script engine", system: "System" };
const modeLabels: Record<ControlMode, string> = { direct: "Direct", command: "Command", assisted: "Assisted", autonomous: "Autonomous", scripted: "Scripted" };
const base = (projectId: string) => `/api/projects/${projectId}/production`;

export default function ProductionStudio({ projectId, phase, scenes, members, currentUserId, canManage }: Props) {
  const [runs, setRuns] = useState<SceneRun[]>([]);
  const [takes, setTakes] = useState<Take[]>([]);
  const [sequences, setSequences] = useState<EditSequence[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedTakeId, setSelectedTakeId] = useState("");
  const [selectedSequenceId, setSelectedSequenceId] = useState("");
  const [sceneId, setSceneId] = useState("");
  const [sequenceName, setSequenceName] = useState("Assembly 01");
  const [eventType, setEventType] = useState("performance_marker");
  const [eventTimestamp, setEventTimestamp] = useState("1000");
  const [eventPayload, setEventPayload] = useState('{"note":"Blocking mark"}');
  const [eventInstanceId, setEventInstanceId] = useState("");
  const [controllerDrafts, setControllerDrafts] = useState<Record<string, { controller_type: ControllerType; controller_user_id: string; control_mode: ControlMode }>>({});
  const [leases, setLeases] = useState<Record<string, Lease>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [exportManifest, setExportManifest] = useState<Record<string, any> | null>(null);

  async function refresh() {
    const [runRows, takeRows, sequenceRows] = await Promise.all([
      api<SceneRun[]>(`${base(projectId)}/scene-runs`),
      api<Take[]>(`${base(projectId)}/takes`),
      api<EditSequence[]>(`${base(projectId)}/edit-sequences`),
    ]);
    setRuns(runRows); setTakes(takeRows); setSequences(sequenceRows);
    if (!selectedRunId && runRows.length) setSelectedRunId(runRows[0].id);
    if (!selectedTakeId && takeRows.length) setSelectedTakeId(takeRows[0].id);
    if (!selectedSequenceId && sequenceRows.length) setSelectedSequenceId(sequenceRows[0].id);
  }

  useEffect(() => {
    let alive = true;
    Promise.all([
      api<SceneRun[]>(`${base(projectId)}/scene-runs`),
      api<Take[]>(`${base(projectId)}/takes`),
      api<EditSequence[]>(`${base(projectId)}/edit-sequences`),
    ]).then(([runRows, takeRows, sequenceRows]) => {
      if (!alive) return;
      setRuns(runRows); setTakes(takeRows); setSequences(sequenceRows);
      if (runRows.length) setSelectedRunId(runRows[0].id);
      if (takeRows.length) setSelectedTakeId(takeRows[0].id);
      if (sequenceRows.length) setSelectedSequenceId(sequenceRows[0].id);
    }).catch(err => { if (alive) setError(err instanceof Error ? err.message : "Could not load production studio."); });
    return () => { alive = false; };
  }, [projectId]);

  const selectedRun = runs.find(item => item.id === selectedRunId) || null;
  const selectedTake = takes.find(item => item.id === selectedTakeId) || null;
  const selectedSequence = sequences.find(item => item.id === selectedSequenceId) || null;
  const runTakes = useMemo(() => selectedRun ? takes.filter(item => item.scene_run_id === selectedRun.id) : [], [takes, selectedRun]);
  const selectedScene = selectedRun ? scenes.find(scene => scene.id === selectedRun.scene_id) : null;
  const writable = canManage && phase === "production";

  async function perform(action: () => Promise<void>, success: string) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); setNotice(success); }
    catch (err) { setError(err instanceof Error ? err.message : "The production action failed."); }
    finally { setBusy(false); }
  }

  async function createRun(event: FormEvent) {
    event.preventDefault();
    if (!sceneId) return;
    await perform(async () => {
      const created = await api<SceneRun>(`${base(projectId)}/scene-runs`, { method: "POST", body: JSON.stringify({ scene_id: sceneId }) });
      await refresh(); setSelectedRunId(created.id);
    }, "A new isolated scene run has been created.");
  }

  async function transitionRun(status: "running" | "paused" | "completed" | "abandoned") {
    if (!selectedRun) return;
    await perform(async () => {
      await api<SceneRun>(`${base(projectId)}/scene-runs/${selectedRun.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await refresh();
    }, `Scene run ${status}.`);
  }

  async function updateController(instance: CastMember) {
    const draft = controllerDrafts[instance.id] || {
      controller_type: instance.controller_type, controller_user_id: instance.controller_user_id || currentUserId || "",
      control_mode: instance.control_mode,
    };
    await perform(async () => {
      await api<CastMember>(`${base(projectId)}/scene-runs/${selectedRun!.id}/instances/${instance.id}/controller`, {
        method: "POST",
        body: JSON.stringify({
          controller_type: draft.controller_type,
          controller_user_id: draft.controller_type === "user" ? draft.controller_user_id : null,
          control_mode: draft.control_mode, reason: "production_studio_assignment",
        }),
      });
      await refresh();
    }, "Controller handoff recorded with a new authority epoch.");
  }

  async function acquireLease(instance: CastMember) {
    await perform(async () => {
      const lease = await api<Lease>(`${base(projectId)}/scene-runs/${selectedRun!.id}/instances/${instance.id}/lease`, {
        method: "POST", body: JSON.stringify({ duration_seconds: 30 }),
      });
      setLeases(current => ({ ...current, [instance.id]: lease }));
    }, "Direct-control possession acquired for 30 seconds.");
  }

  async function releaseLease(instance: CastMember) {
    const lease = leases[instance.id];
    if (!lease) return;
    await perform(async () => {
      await api(`${base(projectId)}/scene-runs/${selectedRun!.id}/instances/${instance.id}/lease/release`, {
        method: "POST", body: JSON.stringify({ lease_token: lease.lease_token }),
      });
      setLeases(current => { const next = { ...current }; delete next[instance.id]; return next; });
    }, "Possession released.");
  }

  async function createTake() {
    if (!selectedRun) return;
    await perform(async () => {
      const created = await api<Take>(`${base(projectId)}/scene-runs/${selectedRun.id}/takes`, {
        method: "POST", body: JSON.stringify({ state_snapshot: { cast_members: selectedRun.cast_members.map(item => ({ instance_id: item.id, state: item.state_snapshot })) } }),
      });
      await refresh(); setSelectedTakeId(created.id);
    }, "New take created. Add ordered performance events to make it replayable.");
  }

  async function recordEvent(event: FormEvent) {
    event.preventDefault();
    if (!selectedTake || !selectedRun) return;
    await perform(async () => {
      let payload: Record<string, unknown>;
      try { payload = JSON.parse(eventPayload) as Record<string, unknown>; }
      catch { throw new Error("Event payload must be valid JSON."); }
      const instance = selectedRun.cast_members.find(item => item.id === eventInstanceId);
      await api<Take>(`${base(projectId)}/takes/${selectedTake.id}/events`, {
        method: "POST",
        body: JSON.stringify({ events: [{
          timestamp_ms: Number(eventTimestamp), event_type: eventType,
          cast_member_instance_id: instance?.id || null,
          authority_epoch: instance?.authority_epoch || null, payload,
        }] }),
      });
      await refresh();
    }, "Performance event appended to the take.");
  }

  async function chooseTake(take: Take) {
    await perform(async () => {
      await api<Take>(`${base(projectId)}/takes/${take.id}`, {
        method: "PATCH", body: JSON.stringify({ status: "selected" }),
      });
      await refresh(); setSelectedTakeId(take.id);
    }, "Take selected for editorial use.");
  }

  async function createSequence(event: FormEvent) {
    event.preventDefault();
    await perform(async () => {
      const created = await api<EditSequence>(`${base(projectId)}/edit-sequences`, {
        method: "POST", body: JSON.stringify({ name: sequenceName }),
      });
      await refresh(); setSelectedSequenceId(created.id);
    }, "Edit sequence created.");
  }

  async function addSelectedTake() {
    if (!selectedTake || !selectedSequence) return;
    await perform(async () => {
      const sceneRun = runs.find(item => item.id === selectedTake.scene_run_id);
      if (!sceneRun) throw new Error("The selected take's scene run is missing.");
      await api<EditSequence>(`${base(projectId)}/edit-sequences/${selectedSequence.id}/items`, {
        method: "POST", body: JSON.stringify({
          take_id: selectedTake.id, in_ms: 0, out_ms: selectedTake.duration_ms,
          transition: "cut", title_overlay: "", effects: {}, audio_cue: "",
        }),
      });
      await refresh();
    }, "Selected take added to the edit timeline.");
  }

  async function moveItem(item: EditItem, direction: -1 | 1) {
    if (!selectedSequence) return;
    const sorted = [...selectedSequence.items].sort((a,b) => a.item_order - b.item_order);
    const index = sorted.findIndex(row => row.id === item.id);
    const target = index + direction;
    if (target < 0 || target >= sorted.length) return;
    [sorted[index], sorted[target]] = [sorted[target], sorted[index]];
    await perform(async () => {
      await api<EditSequence>(`${base(projectId)}/edit-sequences/${selectedSequence.id}/reorder`, {
        method: "PUT", body: JSON.stringify({ item_ids: sorted.map(row => row.id) }),
      });
      await refresh();
    }, "Timeline order updated.");
  }

  async function exportSequence() {
    if (!selectedSequence) return;
    await perform(async () => {
      const result = await api<{ manifest: Record<string, any> }>(`${base(projectId)}/edit-sequences/${selectedSequence.id}/export`, { method: "POST" });
      setExportManifest(result.manifest);
      const blob = new Blob([JSON.stringify(result.manifest, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a"); anchor.href = url;
      anchor.download = `${selectedSequence.name.replace(/[^a-z0-9-_]+/gi, "-").toLowerCase()}-edit-decision-list.json`;
      anchor.click(); URL.revokeObjectURL(url);
      await refresh();
    }, "Immutable edit decision list exported. Video rendering is not yet part of this milestone.");
  }

  if (phase !== "production") return <section className="production-studio">
    <div className="section-kicker">M2.1–M3 · PRODUCTION</div><h2>Production studio</h2>
    <p className="muted-note">The project must enter the production phase before scene runs, takes and editorial sequences can be created.</p>
  </section>;

  return <section className="production-studio">
    <div className="section-heading contribution-heading">
      <div><div className="section-kicker">M2.1 · M2.2 · M3 · VIRTUAL PRODUCTION</div><h2>Production studio</h2></div>
      <span className="step-count">{runs.length} scene runs · {takes.length} takes</span>
    </div>
    <p className="production-studio-intro">A scene run is an isolated execution of an approved storyboard scene. Cast instances snapshot the performer, character and controller at run creation; recorded takes preserve ordered events independently from later edits.</p>
    {error && <div className="casting-alert error">{error}</div>}
    {notice && <div className="casting-alert success">{notice}</div>}

    <div className="production-workspace-grid">
      <section className="production-panel">
        <div className="casting-panel-heading"><div><div className="section-kicker">M2.1 · SCENE RUNTIME</div><h3>Scene runs</h3></div><Activity size={17} /></div>
        {writable && <form className="production-inline-form" onSubmit={createRun}>
          <select value={sceneId} onChange={event => setSceneId(event.target.value)} aria-label="Choose storyboard scene">
            <option value="">Choose a scene…</option>{scenes.map(scene => <option key={scene.id} value={scene.id}>{scene.title}</option>)}
          </select>
          <button className="secondary-button" disabled={busy || !sceneId}><Plus size={13} /> Create run</button>
        </form>}
        <div className="production-run-list">
          {runs.length === 0 && <p className="muted-note">No scene runs yet. Choose a storyboard scene to create the first runtime instance.</p>}
          {runs.map(run => <button type="button" className={`production-run-row ${run.id === selectedRunId ? "selected" : ""}`} key={run.id} onClick={() => setSelectedRunId(run.id)}>
            <span><strong>{run.scene_snapshot.scene?.title || scenes.find(s => s.id === run.scene_id)?.title || "Scene"} · Run {run.run_number}</strong><small>{run.cast_members.length} cast instances · {new Date(run.created_at).toLocaleString()}</small></span>
            <span className={`production-status ${run.status}`}>{run.status}</span>
          </button>)}
        </div>
      </section>

      <section className="production-panel production-runtime-panel">
        <div className="casting-panel-heading"><div><div className="section-kicker">LIVE SET</div><h3>{selectedRun?.scene_snapshot.scene?.title || selectedScene?.title || "Select a scene run"}</h3></div><Camera size={17} /></div>
        {selectedRun ? <>
          <ThreeSceneViewport castMembers={selectedRun.cast_members} sceneTitle={selectedRun.scene_snapshot.scene?.title || "Scene"} />
          <div className="production-run-controls">
            <span className={`production-status ${selectedRun.status}`}>{selectedRun.status}</span>
            {writable && selectedRun.status === "ready" && <button className="primary-button" disabled={busy} onClick={() => transitionRun("running")}><Play size={13} /> Start run</button>}
            {writable && selectedRun.status === "running" && <><button className="secondary-button" disabled={busy} onClick={() => transitionRun("paused")}><Pause size={13} /> Pause</button><button className="quiet-button" disabled={busy} onClick={() => transitionRun("completed")}><Square size={12} /> Complete</button></>}
            {writable && selectedRun.status === "paused" && <><button className="primary-button" disabled={busy} onClick={() => transitionRun("running")}><Play size={13} /> Resume</button><button className="quiet-button" disabled={busy} onClick={() => transitionRun("completed")}><Check size={13} /> Complete</button></>}
            {writable && selectedRun.status === "ready" && <button className="quiet-button" disabled={busy} onClick={() => transitionRun("abandoned")}>Abandon</button>}
            {writable && ["paused","completed"].includes(selectedRun.status) && <button className="secondary-button" disabled={busy} onClick={createTake}><Video size={13} /> Create take</button>}
          </div>
        </> : <div className="production-viewport-empty"><Clapperboard size={26} /><span>Choose or create a scene run to load the set.</span></div>}
      </section>
    </div>

    {selectedRun && <section className="production-panel production-cast-runtime">
      <div className="casting-panel-heading"><div><div className="section-kicker">CAST MEMBER INSTANCES</div><h3>Who is performing each role?</h3></div><UserRound size={17} /></div>
      {selectedRun.cast_members.length === 0 && <p className="muted-note">This scene has no character instances.</p>}
      {selectedRun.cast_members.map(instance => {
        const draft = controllerDrafts[instance.id] || { controller_type: instance.controller_type, controller_user_id: instance.controller_user_id || currentUserId || "", control_mode: instance.control_mode };
        const lease = leases[instance.id];
        const canPossess = selectedRun.status === "running" && instance.controller_type === "user" && instance.controller_user_id === currentUserId;
        return <article className="runtime-cast-row" key={instance.id}>
          <div className="runtime-cast-identity"><strong>{instance.character_snapshot.name}</strong><span>{instance.actor_snapshot.display_name}</span><small>Authority epoch {instance.authority_epoch}</small></div>
          <div className="runtime-controller-fields">
            <label>Controller<select disabled={!writable || ["completed","abandoned"].includes(selectedRun.status)} value={draft.controller_type} onChange={event => setControllerDrafts(current => ({ ...current, [instance.id]: { ...draft, controller_type: event.target.value as ControllerType } }))}>
              {Object.entries(controllerLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            {draft.controller_type === "user" && <label>Member<select disabled={!writable} value={draft.controller_user_id} onChange={event => setControllerDrafts(current => ({ ...current, [instance.id]: { ...draft, controller_user_id: event.target.value } }))}>
              <option value="">Choose member</option>{members.filter(member => member.status === "active" && member.user_id).map(member => <option key={member.id} value={member.user_id || ""}>{member.display_name || member.email || "Member"}</option>)}
            </select></label>}
            <label>Control mode<select disabled={!writable} value={draft.control_mode} onChange={event => setControllerDrafts(current => ({ ...current, [instance.id]: { ...draft, control_mode: event.target.value as ControlMode } }))}>
              {Object.entries(modeLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            {writable && <button className="secondary-button" disabled={busy || (draft.controller_type === instance.controller_type && draft.controller_user_id === (instance.controller_user_id || "") && draft.control_mode === instance.control_mode)} onClick={() => updateController(instance)}><Save size={12} /> Handoff</button>}
          </div>
          {canPossess && <div className="runtime-lease-controls">
            {lease ? <><span><Lock size={12} /> Lease active until {new Date(lease.expires_at).toLocaleTimeString()}</span><button className="quiet-button" disabled={busy} onClick={() => releaseLease(instance)}>Release</button></> :
              <button className="quiet-button" disabled={busy} onClick={() => acquireLease(instance)}><Radio size={12} /> Take direct control</button>}
          </div>}
        </article>;
      })}
    </section>}

    <div className="production-workspace-grid production-lower-grid">
      <section className="production-panel">
        <div className="casting-panel-heading"><div><div className="section-kicker">M2.2 · PERFORMANCE RECORDING</div><h3>Takes & event stream</h3></div><CircleDot size={17} /></div>
        <label className="production-select-label">Scene run<select value={selectedRunId} onChange={event => setSelectedRunId(event.target.value)}><option value="">Choose run</option>{runs.map(run => <option key={run.id} value={run.id}>{run.scene_snapshot.scene?.title || "Scene"} · Run {run.run_number}</option>)}</select></label>
        <label className="production-select-label">Take<select value={selectedTakeId} onChange={event => setSelectedTakeId(event.target.value)}><option value="">Choose take</option>{takes.map(take => <option key={take.id} value={take.id}>Take {take.take_number} · {take.status} · {take.duration_ms} ms</option>)}</select></label>
        {selectedTake && <>
          <div className="take-metrics"><div><strong>{selectedTake.event_count}</strong><span>Events</span></div><div><strong>{selectedTake.duration_ms} ms</strong><span>Duration</span></div><div><strong>{selectedTake.status}</strong><span>Editorial state</span></div></div>
          {writable && selectedTake.status === "recorded" && <form className="casting-form" onSubmit={recordEvent}>
            <div className="section-kicker">APPEND EVENT</div>
            <label>Event type<input value={eventType} onChange={event => setEventType(event.target.value)} maxLength={60} /></label>
            <label>Timestamp (ms)<input type="number" min="0" value={eventTimestamp} onChange={event => setEventTimestamp(event.target.value)} /></label>
            <label>Cast member<select value={eventInstanceId} onChange={event => setEventInstanceId(event.target.value)}><option value="">Scene-level event</option>{selectedRun?.cast_members.map(item => <option key={item.id} value={item.id}>{item.character_snapshot.name}</option>)}</select></label>
            <label>Payload (JSON)<textarea rows={3} value={eventPayload} onChange={event => setEventPayload(event.target.value)} /></label>
            <button className="secondary-button" disabled={busy || !eventType.trim()}><Plus size={12} /> Record event</button>
          </form>}
          <div className="take-event-list">{selectedTake.events.map(item => <div key={item.id}><small>{item.timestamp_ms} ms · #{item.event_order}</small><strong>{item.event_type}</strong><code>{JSON.stringify(item.payload)}</code></div>)}</div>
          {writable && selectedTake.status === "recorded" && selectedTake.event_count > 0 && <button className="primary-button" disabled={busy} onClick={() => chooseTake(selectedTake)}><Check size={13} /> Select take</button>}
        </>}
        {!selectedTake && <p className="muted-note">Pause or complete a run to create a take. Add ordered event records to make it replayable.</p>}
      </section>

      <section className="production-panel">
        <div className="casting-panel-heading"><div><div className="section-kicker">M3 · NON-DESTRUCTIVE EDITING</div><h3>Assembly timeline</h3></div><Film size={17} /></div>
        {writable && <form className="production-inline-form" onSubmit={createSequence}>
          <input value={sequenceName} onChange={event => setSequenceName(event.target.value)} aria-label="New edit sequence name" placeholder="Sequence name" />
          <button className="secondary-button" disabled={busy || !sequenceName.trim()}><Plus size={12} /> New sequence</button>
        </form>}
        <label className="production-select-label">Edit sequence<select value={selectedSequenceId} onChange={event => setSelectedSequenceId(event.target.value)}><option value="">Choose sequence</option>{sequences.map(item => <option key={item.id} value={item.id}>{item.name} · Rev {item.revision_number}</option>)}</select></label>
        {selectedSequence && <>
          <div className="production-sequence-heading"><strong>{selectedSequence.name}</strong><span>Revision {selectedSequence.revision_number} · {selectedSequence.items.length} clips</span></div>
          {writable && selectedTake?.status === "selected" && selectedTake.duration_ms > 0 && <button className="secondary-button" disabled={busy || selectedSequence.status !== "draft"} onClick={addSelectedTake}><Plus size={12} /> Add selected take to timeline</button>}
          <div className="edit-timeline">
            {selectedSequence.items.length === 0 && <p className="muted-note">Select a recorded take and add it to this sequence.</p>}
            {[...selectedSequence.items].sort((a,b) => a.item_order-b.item_order).map(item => {
              const take = takes.find(row => row.id === item.take_id);
              const scene = scenes.find(row => row.id === item.scene_id);
              return <article className="edit-timeline-item" key={item.id}>
                <div><small>CLIP {item.item_order.toString().padStart(2,"0")} · {item.transition}</small><strong>{scene?.title || "Scene"} · Take {take?.take_number}</strong><span>{item.in_ms}–{item.out_ms} ms · {item.out_ms-item.in_ms} ms</span></div>
                <div className="edit-item-order-controls"><button type="button" aria-label="Move clip up" disabled={!writable || item.item_order===1 || busy} onClick={() => moveItem(item,-1)}><ChevronUp size={14}/></button><button type="button" aria-label="Move clip down" disabled={!writable || item.item_order===selectedSequence.items.length || busy} onClick={() => moveItem(item,1)}><ChevronDown size={14}/></button></div>
              </article>;
            })}
          </div>
          {writable && selectedSequence.items.length > 0 && <button className="primary-button" disabled={busy} onClick={exportSequence}><Download size={13} /> Export edit decision list</button>}
          {exportManifest && <p className="muted-note">Last export: {exportManifest.duration_ms} ms · {exportManifest.clips?.length || 0} clips. Manifest downloaded as JSON.</p>}
          <p className="muted-note">The timeline references immutable selected takes. Trims, transitions, title overlays, effects and audio cues are stored as edit instructions; source performances remain unchanged.</p>
        </>}
      </section>
    </div>
  </section>;
}
