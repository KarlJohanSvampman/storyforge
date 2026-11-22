import { FormEvent, useEffect, useState } from "react";
import { Activity, Camera, Check, ChevronDown, ChevronUp, Clapperboard, Download, Film, Lock, Pause, Play, Plus, Radio, Save, Square, UserRound, Video } from "lucide-react";
import ThreeSceneViewport from "./ThreeSceneViewport";
import type { SceneProductionAsset } from "./productionScene";
import AudioTimeline from "./AudioTimeline";
import ProductionVideoExport from "./ProductionVideoExport";
import MotionCaptureSetup from "./MotionCaptureSetup";

type SceneOption = { id: string; title: string };
type Member = { id: string; user_id: string | null; display_name: string | null; email: string | null; role: string; status: string };
type ControllerType = "user" | "ai_agent" | "script_engine" | "system";
type ControlMode = "direct" | "command" | "assisted" | "autonomous" | "scripted";
type CastMember = {
  id: string; actor_name_snapshot: string; character_name_snapshot: string; role_label_snapshot: string;
  controller_type: ControllerType; controller_user_id: string | null; control_mode: ControlMode;
  authority_epoch: number; instance_status: string;
};
type SceneRun = {
  id: string; scene_id: string; scene_title: string; location_id: string | null; status: "prepared" | "running" | "paused" | "completed" | "aborted";
  authority_epoch: number; cast_members: CastMember[]; created_at: string; started_at: string | null; ended_at: string | null;
};
type TakeEvent = { id: string; sequence_number: number; timestamp_ms: number; event_type: string; cast_member_instance_id: string | null; authority_epoch: number | null; payload: Record<string, unknown> };
type PerformanceAnnotation = { id: string; timestamp_ms: number; category: string; content: string; status: "open" | "resolved"; author_display_name: string };
type ReplayData = { duration_ms: number; events: TakeEvent[]; annotations: PerformanceAnnotation[]; playback_capabilities: Record<string, unknown> };
type Take = {
  id: string; scene_run_id: string; cast_member_instance_id: string | null; take_number: number;
  title: string; status: "recording" | "finalized" | "selected" | "discarded";
  duration_ms: number | null; camera_snapshot: Record<string, unknown>; state_snapshot: Record<string, unknown>;
  events: TakeEvent[];
};
type EditItem = { id: string; take_id: string; scene_id: string; item_order: number; in_ms: number; out_ms: number; transition: string; title_overlay: string; effects: Record<string, unknown>; audio_cue: string };
type EditItemDraft = { in_ms: string; out_ms: string; transition: "cut" | "fade" | "dissolve"; title_overlay: string; effects: string; audio_cue: string };
type EditSequence = { id: string; name: string; status: string; revision_number: number; items: EditItem[] };
type Lease = { id: string; lease_token: string; expires_at: string; authority_epoch: number };
type Props = { projectId: string; phase: string; scenes: SceneOption[]; members: Member[]; currentUserId: string | null; canManage: boolean; onPhaseChanged: () => Promise<void> };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const root = (projectId: string) => `/api/projects/${projectId}`;
const controllerLabels: Record<ControllerType, string> = { user: "Human", ai_agent: "AI agent", script_engine: "Script engine", system: "System" };
const modeLabels: Record<ControlMode, string> = { direct: "Direct", command: "Command", assisted: "Assisted", autonomous: "Autonomous", scripted: "Scripted" };
type CameraPreset = "wide" | "close" | "overhead" | "reverse";

export default function ProductionStudio({ projectId, phase, scenes, members, currentUserId, canManage, onPhaseChanged }: Props) {
  const [runs, setRuns] = useState<SceneRun[]>([]);
  const [productionAssets, setProductionAssets] = useState<SceneProductionAsset[]>([]);
  const [takes, setTakes] = useState<Take[]>([]);
  const [sequences, setSequences] = useState<EditSequence[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedTakeId, setSelectedTakeId] = useState("");
  const [selectedSequenceId, setSelectedSequenceId] = useState("");
  const [sceneId, setSceneId] = useState("");
  const [sequenceName, setSequenceName] = useState("Assembly 01");
  const [takeTitle, setTakeTitle] = useState("Take");
  const [eventType, setEventType] = useState<"transform" | "gesture" | "expression" | "voice_marker" | "camera" | "cue">("cue");
  const [eventTimestamp, setEventTimestamp] = useState("0");
  const [eventPayload, setEventPayload] = useState('{"note":"Blocking marker"}');
  const [eventInstanceId, setEventInstanceId] = useState("");
  const [durationInput, setDurationInput] = useState("30000");
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>("wide");
  const [replayData, setReplayData] = useState<ReplayData | null>(null);
  const [playheadMs, setPlayheadMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [annotationDraft, setAnnotationDraft] = useState("");
  const [controllerDrafts, setControllerDrafts] = useState<Record<string, { controller_type: ControllerType; controller_user_id: string; control_mode: ControlMode }>>({});
  const [leases, setLeases] = useState<Record<string, Lease>>({});
  const [itemDrafts, setItemDrafts] = useState<Record<string, EditItemDraft>>({});
  const [exportManifest, setExportManifest] = useState<Record<string, any> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function refresh() {
    const [runRows, takeRows, sequenceRows] = await Promise.all([
      api<SceneRun[]>(`${root(projectId)}/scene-runs`),
      api<Take[]>(`${root(projectId)}/takes`),
      api<EditSequence[]>(`${root(projectId)}/edit-sequences`),
    ]);
    setRuns(runRows); setTakes(takeRows); setSequences(sequenceRows);
    if (!selectedRunId && runRows.length) setSelectedRunId(runRows[0].id);
    if (!selectedTakeId && takeRows.length) setSelectedTakeId(takeRows[0].id);
    if (!selectedSequenceId && sequenceRows.length) setSelectedSequenceId(sequenceRows[0].id);
  }

  useEffect(() => {
    let alive = true;
    api<any[]>(root(projectId) + "/production-assets/bindings")
      .then(rows => {
        if (!alive) return;
        setProductionAssets(rows.map(row => ({
          asset_id: row.asset.id,
          target_type: row.target_type,
          target_id: row.target_id,
          version: row.asset.version,
          sha256: row.asset.sha256,
          file_format: row.asset.file_format,
          render_url: row.asset.download_url,
          download_url: row.asset.download_url,
          transform: row.transform_json || { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
        })));
      })
      .catch(() => { if (alive) setProductionAssets([]); });
    return () => { alive = false; };
  }, [projectId]);

  useEffect(() => {
    let alive = true;
    Promise.all([
      api<SceneRun[]>(`${root(projectId)}/scene-runs`),
      api<Take[]>(`${root(projectId)}/takes`),
      api<EditSequence[]>(`${root(projectId)}/edit-sequences`),
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
  const takeRun = selectedTake ? runs.find(item => item.id === selectedTake.scene_run_id) || null : null;
  const selectedSequence = sequences.find(item => item.id === selectedSequenceId) || null;
  const writable = canManage && phase === "production";

  useEffect(() => {
    let alive = true;
    setIsPlaying(false); setPlayheadMs(0); setReplayData(null);
    if (!selectedTake || !["finalized", "selected"].includes(selectedTake.status)) return;
    api<ReplayData>(`${root(projectId)}/takes/${selectedTake.id}/replay`)
      .then(data => { if (alive) setReplayData(data); })
      .catch(err => { if (alive) setError(err instanceof Error ? err.message : "Could not load take replay."); });
    return () => { alive = false; };
  }, [projectId, selectedTake?.id, selectedTake?.status]);

  useEffect(() => {
    if (!isPlaying || !replayData) return;
    let frame = 0;
    let previous = performance.now();
    const tick = (now: number) => {
      const delta = now - previous; previous = now;
      setPlayheadMs(current => {
        const next = Math.min(replayData.duration_ms, current + delta);
        if (next >= replayData.duration_ms) setIsPlaying(false);
        return next;
      });
      if (now < previous + 100000 && isPlaying) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [isPlaying, replayData]);


  useEffect(() => {
    if (selectedTake) {
      const latest = Math.max(0, ...selectedTake.events.map(item => item.timestamp_ms));
      setEventTimestamp(String(latest + 250));
      setEventInstanceId("");
    }
  }, [selectedTake?.id]);

  useEffect(() => {
    if (!selectedSequence) return;
    setItemDrafts(Object.fromEntries(selectedSequence.items.map(item => [item.id, {
      in_ms: String(item.in_ms), out_ms: String(item.out_ms),
      transition: item.transition as EditItemDraft["transition"],
      title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue,
    }])));
  }, [selectedSequence?.id, selectedSequence?.revision_number]);

  async function perform(action: () => Promise<void>, success: string) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); setNotice(success); }
    catch (err) { setError(err instanceof Error ? err.message : "The production action failed."); }
    finally { setBusy(false); }
  }

  async function activateProduction() {
    await perform(async () => {
      await api(`${root(projectId)}/production/activate`, { method: "POST", body: JSON.stringify({ reason: "Storyboard and cast approved for production." }) });
      await onPhaseChanged();
      await refresh();
    }, "Project entered production.");
  }

  async function createRun(event: FormEvent) {
    event.preventDefault();
    if (!sceneId) return;
    await perform(async () => {
      const created = await api<SceneRun>(`${root(projectId)}/scene-runs`, { method: "POST", body: JSON.stringify({ scene_id: sceneId }) });
      await refresh(); setSelectedRunId(created.id);
    }, "Scene run prepared from the current storyboard and cast.");
  }

  async function transitionRun(status: "running" | "paused" | "completed" | "aborted") {
    if (!selectedRun) return;
    await perform(async () => {
      await api(`${root(projectId)}/scene-runs/${selectedRun.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await refresh();
    }, `Scene run ${status}.`);
  }

  async function updateController(instance: CastMember) {
    const draft = controllerDrafts[instance.id] || {
      controller_type: instance.controller_type, controller_user_id: instance.controller_user_id || currentUserId || "",
      control_mode: instance.control_mode,
    };
    await perform(async () => {
      await api(`${root(projectId)}/scene-runs/${selectedRun!.id}/cast-members/${instance.id}/controller`, {
        method: "POST", body: JSON.stringify({
          controller_type: draft.controller_type,
          controller_user_id: draft.controller_type === "user" ? draft.controller_user_id : null,
          control_mode: draft.control_mode, reason: "production_studio_assignment",
        }),
      });
      await refresh();
      setControllerDrafts(current => ({ ...current, [instance.id]: draft }));
    }, "Controller handoff recorded with a new authority epoch.");
  }

  async function acquireLease(instance: CastMember) {
    await perform(async () => {
      const lease = await api<Lease>(`${root(projectId)}/scene-runs/${selectedRun!.id}/cast-members/${instance.id}/leases`, {
        method: "POST", body: JSON.stringify({ duration_seconds: 30 }),
      });
      setLeases(current => ({ ...current, [instance.id]: lease }));
      await refresh();
    }, "Direct-control possession acquired for 30 seconds.");
  }

  async function releaseLease(instance: CastMember) {
    const lease = leases[instance.id];
    if (!lease) return;
    await perform(async () => {
      await api(`${root(projectId)}/scene-runs/${selectedRun!.id}/cast-members/${instance.id}/leases/release`, {
        method: "POST", body: JSON.stringify({ lease_token: lease.lease_token }),
      });
      setLeases(current => { const next = { ...current }; delete next[instance.id]; return next; });
      await refresh();
    }, "Possession released and prior controller restored.");
  }

  async function createTake() {
    if (!selectedRun) return;
    await perform(async () => {
      const created = await api<Take>(`${root(projectId)}/scene-runs/${selectedRun.id}/takes`, {
        method: "POST", body: JSON.stringify({
          title: takeTitle, camera_snapshot: { preset: cameraPreset },
          state_snapshot: { cast_members: selectedRun.cast_members.map(item => ({ instance_id: item.id, actor: item.actor_name_snapshot, character: item.character_name_snapshot })) },
        }),
      });
      await refresh(); setSelectedTakeId(created.id);
    }, "Take recording started.");
  }

  async function appendEvent(type: "transform" | "gesture" | "expression" | "voice_marker" | "camera" | "cue", timestamp: number, payload: Record<string, unknown>, instanceId?: string) {
    if (!selectedTake || !takeRun) return;
    const instance = instanceId ? takeRun.cast_members.find(item => item.id === instanceId) : undefined;
    const next = selectedTake.events.length ? Math.max(...selectedTake.events.map(item => item.sequence_number)) + 1 : 0;
    await api<Take>(`${root(projectId)}/takes/${selectedTake.id}/events`, {
      method: "POST", body: JSON.stringify([{
        sequence_number: next, timestamp_ms: timestamp, event_type: type,
        cast_member_instance_id: instance?.id || null,
        authority_epoch: instance?.authority_epoch || null, payload,
      }]),
    });
    await refresh();
  }

  async function recordEvent(event: FormEvent) {
    event.preventDefault();
    if (!selectedTake || selectedTake.status !== "recording") return;
    await perform(async () => {
      let payload: Record<string, unknown>;
      try { payload = JSON.parse(eventPayload) as Record<string, unknown>; }
      catch { throw new Error("Event payload must be valid JSON."); }
      await appendEvent(eventType, Number(eventTimestamp), payload, eventInstanceId || undefined);
      setEventTimestamp(String(Number(eventTimestamp) + 250));
    }, "Performance event appended to the take.");
  }

  async function changeCamera(preset: CameraPreset) {
    setCameraPreset(preset);
    if (selectedTake?.status === "recording" && selectedTake.scene_run_id === selectedRun?.id) {
      await perform(async () => {
        const started = selectedRun?.started_at ? new Date(selectedRun.started_at).getTime() : Date.now();
        const timestamp = Math.max(0, Date.now() - started);
        await appendEvent("camera", timestamp, { preset });
        setEventTimestamp(String(timestamp + 250));
      }, "Virtual camera cut recorded.");
    }
  }

  async function finalizeTake() {
    if (!selectedTake) return;
    await perform(async () => {
      const latest = Math.max(0, ...selectedTake.events.map(item => item.timestamp_ms));
      const duration = Math.max(Number(durationInput) || 0, latest);
      await api<Take>(`${root(projectId)}/takes/${selectedTake.id}/finalize`, {
        method: "POST", body: JSON.stringify({ duration_ms: duration }),
      });
      await refresh();
    }, "Take finalized and made immutable.");
  }

  async function chooseTake(take: Take) {
    await perform(async () => {
      await api<Take>(`${root(projectId)}/takes/${take.id}/select`, { method: "POST" });
      await refresh(); setSelectedTakeId(take.id);
    }, "Take selected for editorial use.");
  }

  async function createSequence(event: FormEvent) {
    event.preventDefault();
    await perform(async () => {
      const created = await api<EditSequence>(`${root(projectId)}/edit-sequences`, {
        method: "POST", body: JSON.stringify({ name: sequenceName }),
      });
      await refresh(); setSelectedSequenceId(created.id);
    }, "Edit sequence created.");
  }

  async function addSelectedTake() {
    if (!selectedTake || !selectedSequence || !selectedTake.duration_ms) return;
    await perform(async () => {
      const run = runs.find(item => item.id === selectedTake.scene_run_id);
      if (!run) throw new Error("The selected take's scene run is missing.");
      await api<EditSequence>(`${root(projectId)}/edit-sequences/${selectedSequence.id}/items`, {
        method: "POST", body: JSON.stringify({
          take_id: selectedTake.id, in_ms: 0, out_ms: selectedTake.duration_ms,
          transition: "cut", title_overlay: "", effects: {}, audio_cue: "",
        }),
      });
      await refresh();
    }, "Selected take added to the edit timeline.");
  }

  async function saveEditItem(item: EditItem) {
    if (!selectedSequence) return;
    const draft = itemDrafts[item.id];
    if (!draft) return;
    await perform(async () => {
      let effects: Record<string, unknown>;
      try { effects = JSON.parse(draft.effects) as Record<string, unknown>; }
      catch { throw new Error("Effect settings must be valid JSON."); }
      await api<EditSequence>(`${root(projectId)}/edit-sequences/${selectedSequence.id}/items/${item.id}`, {
        method: "PATCH", body: JSON.stringify({
          in_ms: Number(draft.in_ms), out_ms: Number(draft.out_ms), transition: draft.transition,
          title_overlay: draft.title_overlay, effects, audio_cue: draft.audio_cue,
        }),
      });
      await refresh();
    }, "Clip edit instructions saved as a new sequence revision.");
  }

  async function deleteEditItem(item: EditItem) {
    if (!selectedSequence) return;
    await perform(async () => {
      await api<EditSequence>(`${root(projectId)}/edit-sequences/${selectedSequence.id}/items/${item.id}`, { method: "DELETE" });
      await refresh();
    }, "Clip removed. The source take remains untouched.");
  }

  async function moveItem(item: EditItem, direction: -1 | 1) {
    if (!selectedSequence) return;
    const sorted = [...selectedSequence.items].sort((a,b) => a.item_order - b.item_order);
    const index = sorted.findIndex(row => row.id === item.id);
    const target = index + direction;
    if (target < 0 || target >= sorted.length) return;
    [sorted[index], sorted[target]] = [sorted[target], sorted[index]];
    await perform(async () => {
      await api<EditSequence>(`${root(projectId)}/edit-sequences/${selectedSequence.id}/reorder`, {
        method: "PUT", body: JSON.stringify({ item_ids: sorted.map(row => row.id) }),
      });
      await refresh();
    }, "Timeline order updated.");
  }

  async function exportSequence() {
    if (!selectedSequence) return;
    await perform(async () => {
      const result = await api<{ manifest: Record<string, any> }>(`${root(projectId)}/edit-sequences/${selectedSequence.id}/export`, { method: "POST" });
      setExportManifest(result.manifest);
      const blob = new Blob([JSON.stringify(result.manifest, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a"); anchor.href = url;
      anchor.download = `${selectedSequence.name.replace(/[^a-z0-9-_]+/gi, "-").toLowerCase()}-edit-decision-list.json`;
      anchor.click(); URL.revokeObjectURL(url);
    }, "Immutable edit decision list exported. Video rendering remains a later milestone.");
  }

  if (phase === "storyboard") return <section className="production-studio">
    <div className="section-kicker">M2.1 · PRODUCTION HANDOFF</div><h2>Ready to enter production?</h2>
    <p className="production-studio-intro">The storyboard and cast are the source for runtime instances. Entering production enables the runtime, performance and editorial workspace.</p>
    {canManage && <button className="primary-button" disabled={busy} onClick={activateProduction}><Clapperboard size={14} /> Enter production</button>}
    {!canManage && <p className="muted-note">Only the project owner can activate production.</p>}
  </section>;
  if (phase !== "production") return null;

  return <section className="production-studio">
    <div className="section-heading contribution-heading">
      <div><div className="section-kicker">M2.1 · M2.2 · M3 · VIRTUAL PRODUCTION</div><h2>Production studio</h2></div>
      <span className="step-count">{runs.length} scene runs · {takes.length} takes</span>
    </div>
    <p className="production-studio-intro">Run an isolated storyboard scene, direct character controllers, record immutable takes, then assemble selected takes into a non-destructive edit sequence.</p>
    {error && <div className="casting-alert error">{error}</div>}
    {notice && <div className="casting-alert success">{notice}</div>}

    <div className="production-workspace-grid">
      <section className="production-panel">
        <div className="casting-panel-heading"><div><div className="section-kicker">M2.1 · SCENE RUNTIME</div><h3>Scene runs</h3></div><Activity size={17} /></div>
        {writable && <form className="production-inline-form" onSubmit={createRun}>
          <select value={sceneId} onChange={event => setSceneId(event.target.value)} aria-label="Choose storyboard scene">
            <option value="">Choose a scene…</option>{scenes.map(scene => <option key={scene.id} value={scene.id}>{scene.title}</option>)}
          </select>
          <button className="secondary-button" disabled={busy || !sceneId}><Plus size={13} /> Prepare run</button>
        </form>}
        <div className="production-run-list">
          {runs.length === 0 && <p className="muted-note">No scene runs yet. Prepare a scene to create its cast-member instances.</p>}
          {runs.map(run => <button type="button" className={`production-run-row ${run.id === selectedRunId ? "selected" : ""}`} key={run.id} onClick={() => setSelectedRunId(run.id)}>
            <span><strong>{run.scene_title} · {run.id.slice(0,8)}</strong><small>{run.cast_members.length} cast instances · {new Date(run.created_at).toLocaleString()}</small></span>
            <span className={`production-status ${run.status}`}>{run.status}</span>
          </button>)}
        </div>
      </section>

      <section className="production-panel production-runtime-panel">
        <div className="casting-panel-heading"><div><div className="section-kicker">LIVE SET</div><h3>{selectedRun?.scene_title || "Select a scene run"}</h3></div><Camera size={17} /></div>
        {selectedRun ? <>
          <ThreeSceneViewport castMembers={selectedRun.cast_members} productionAssets={productionAssets} sceneLocationId={selectedRun.location_id} sceneTitle={selectedRun.scene_title} cameraPreset={cameraPreset} replayEvents={selectedTake?.scene_run_id === selectedRun.id ? replayData?.events || [] : []} playheadMs={playheadMs} />
          <label className="production-camera-select">Virtual camera<select value={cameraPreset} disabled={selectedRun.status !== "running"} onChange={event => changeCamera(event.target.value as CameraPreset)}>
            <option value="wide">Wide master</option><option value="close">Close-up</option><option value="overhead">Overhead</option><option value="reverse">Reverse angle</option>
          </select></label>
          <div className="production-run-controls">
            <span className={`production-status ${selectedRun.status}`}>{selectedRun.status}</span>
            {writable && selectedRun.status === "prepared" && <button className="primary-button" disabled={busy} onClick={() => transitionRun("running")}><Play size={13} /> Start run</button>}
            {writable && selectedRun.status === "running" && <><button className="secondary-button" disabled={busy} onClick={() => transitionRun("paused")}><Pause size={13} /> Pause</button><button className="quiet-button" disabled={busy} onClick={() => transitionRun("completed")}><Square size={12} /> Complete</button></>}
            {writable && selectedRun.status === "paused" && <><button className="primary-button" disabled={busy} onClick={() => transitionRun("running")}><Play size={13} /> Resume</button><button className="quiet-button" disabled={busy} onClick={() => transitionRun("completed")}><Check size={13} /> Complete</button></>}
            {writable && selectedRun.status === "prepared" && <button className="quiet-button" disabled={busy} onClick={() => transitionRun("aborted")}>Abort</button>}
          </div>
        </> : <div className="production-viewport-empty"><Clapperboard size={26} /><span>Choose or prepare a scene run to load the set.</span></div>}
      </section>
    </div>

    {selectedRun && <MotionCaptureSetup projectId={projectId} sceneRunId={selectedRun.id} castMembers={selectedRun.cast_members} />}

    {selectedRun && <section className="production-panel production-cast-runtime">
      <div className="casting-panel-heading"><div><div className="section-kicker">CAST MEMBER INSTANCES</div><h3>Who is performing each role?</h3></div><UserRound size={17} /></div>
      {selectedRun.cast_members.length === 0 && <p className="muted-note">This scene has no character instances.</p>}
      {selectedRun.cast_members.map(instance => {
        const draft = controllerDrafts[instance.id] || { controller_type: instance.controller_type, controller_user_id: instance.controller_user_id || currentUserId || "", control_mode: instance.control_mode };
        const lease = leases[instance.id];
        const assignedHuman = instance.controller_type === "user" && instance.controller_user_id === currentUserId;
        const directorOverride = members.some(member => member.user_id === currentUserId && (member.role === "owner" || member.role === "editor"));
        const canPossess = selectedRun.status === "running" && !!currentUserId && (assignedHuman || directorOverride);
        return <article className="runtime-cast-row" key={instance.id}>
          <div className="runtime-cast-identity"><strong>{instance.character_name_snapshot}</strong><span>{instance.actor_name_snapshot} · {instance.role_label_snapshot}</span><small>Authority epoch {instance.authority_epoch}</small></div>
          <div className="runtime-controller-fields">
            <label>Controller<select disabled={!writable || ["completed","aborted"].includes(selectedRun.status)} value={draft.controller_type} onChange={event => setControllerDrafts(current => ({ ...current, [instance.id]: { ...draft, controller_type: event.target.value as ControllerType } }))}>
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
        <div className="casting-panel-heading"><div><div className="section-kicker">M2.2 · PERFORMANCE RECORDING</div><h3>Takes & event stream</h3></div><Video size={17} /></div>
        <label className="production-select-label">Scene run<select value={selectedRunId} onChange={event => setSelectedRunId(event.target.value)}><option value="">Choose run</option>{runs.map(run => <option key={run.id} value={run.id}>{run.scene_title} · {run.id.slice(0,8)}</option>)}</select></label>
        <label className="production-select-label">Take<select value={selectedTakeId} onChange={event => setSelectedTakeId(event.target.value)}><option value="">Choose take</option>{takes.map(take => <option key={take.id} value={take.id}>Take {take.take_number} · {take.status} · {take.duration_ms ?? "—"} ms</option>)}</select></label>
        {selectedRun?.status === "running" && writable && <div className="production-inline-form">
          <input value={takeTitle} onChange={event => setTakeTitle(event.target.value)} aria-label="Take title" placeholder="Take title"/>
          <button className="secondary-button" disabled={busy || !takeTitle.trim()} onClick={createTake}><Plus size={12}/> Start take</button>
        </div>}
        {selectedTake && <>
          <div className="take-metrics"><div><strong>{selectedTake.events.length}</strong><span>Events</span></div><div><strong>{selectedTake.duration_ms ?? "Recording"}</strong><span>Duration ms</span></div><div><strong>{selectedTake.status}</strong><span>Editorial state</span></div></div>
          {replayData && <>
            <div className="replay-panel">
              <div className="section-kicker">M3.1 · PERFORMANCE PLAYBACK</div>
              <div className="replay-controls">
                <button type="button" className="secondary-button" onClick={() => { setIsPlaying(false); setPlayheadMs(0); }}>⟲ Start</button>
                <button type="button" className="secondary-button" onClick={() => setIsPlaying(value => !value)}>{isPlaying ? "Pause" : "Play"}</button>
                <button type="button" className="secondary-button" onClick={() => { setIsPlaying(false); setPlayheadMs(Math.max(0, [...replayData.events].filter(event => event.timestamp_ms < playheadMs).sort((a,b) => b.timestamp_ms-a.timestamp_ms)[0]?.timestamp_ms ?? 0)); }}>Previous event</button>
                <button type="button" className="secondary-button" onClick={() => { setIsPlaying(false); setPlayheadMs([...replayData.events].find(event => event.timestamp_ms > playheadMs)?.timestamp_ms ?? replayData.duration_ms); }}>Next event</button>
                <strong>{Math.round(playheadMs)} / {replayData.duration_ms} ms</strong>
              </div>
              <input aria-label="Replay position" className="replay-scrubber" type="range" min="0" max={Math.max(1,replayData.duration_ms)} value={Math.min(playheadMs,replayData.duration_ms)} onChange={event => { setIsPlaying(false); setPlayheadMs(Number(event.target.value)); }} />
              <div className="replay-marker-row">{replayData.events.map(event => <button key={event.id} type="button" title={`${event.event_type} · ${event.timestamp_ms} ms`} style={{ left: `${replayData.duration_ms ? event.timestamp_ms / replayData.duration_ms * 100 : 0}%` }} onClick={() => { setIsPlaying(false); setPlayheadMs(event.timestamp_ms); }} />)}</div>
              <div className="replay-event-strip">{replayData.events.map(event => <button key={event.id} type="button" className={playheadMs >= event.timestamp_ms ? "active" : ""} onClick={() => { setIsPlaying(false); setPlayheadMs(event.timestamp_ms); }}><small>{event.timestamp_ms} ms</small><strong>{event.event_type}</strong></button>)}</div>
              <p className="muted-note">Recorded position, rotation, scale and camera preset events are reconstructed where payloads contain supported values. This is event playback, not a deterministic physics or skeletal-animation replay.</p>
            </div>
            <div className="replay-annotations">
              <div className="section-kicker">DIRECTOR NOTES</div>
              <form className="production-inline-form" onSubmit={async event => {
                event.preventDefault();
                if (!selectedTake || !annotationDraft.trim()) return;
                await perform(async () => {
                  await api(`${root(projectId)}/takes/${selectedTake.id}/annotations`, { method: "POST", body: JSON.stringify({ timestamp_ms: Math.round(playheadMs), content: annotationDraft, category: "note" }) });
                  const refreshed = await api<ReplayData>(`${root(projectId)}/takes/${selectedTake.id}/replay`);
                  setReplayData(refreshed); setAnnotationDraft("");
                }, "Director note saved at the current playhead.");
              }}>
                <input value={annotationDraft} onChange={event => setAnnotationDraft(event.target.value)} placeholder="Add a note at the current time…" aria-label="Director note" />
                <button className="secondary-button" disabled={busy || !annotationDraft.trim()}>Add note</button>
              </form>
              <div className="replay-note-list">{replayData.annotations.map(note => <article key={note.id}><small>{note.timestamp_ms} ms · {note.category} · {note.author_display_name} · {note.status}</small><p>{note.content}</p>{note.status === "open" && canManage && <button type="button" className="quiet-button" disabled={busy} onClick={() => perform(async () => { await api(`${root(projectId)}/takes/${selectedTake.id}/annotations/${note.id}`, { method: "PATCH", body: JSON.stringify({ status: "resolved" }) }); setReplayData(await api<ReplayData>(`${root(projectId)}/takes/${selectedTake.id}/replay`)); }, "Director note resolved.")}>Resolve</button>}</article>)}</div>
            </div>
          </>}

          {writable && selectedTake.status === "recording" && <form className="casting-form" onSubmit={recordEvent}>
            <div className="section-kicker">APPEND EVENT</div>
            <label>Event type<select value={eventType} onChange={event => setEventType(event.target.value as typeof eventType)}>
              <option value="transform">Transform</option><option value="gesture">Gesture</option><option value="expression">Expression</option><option value="voice_marker">Voice marker</option><option value="camera">Camera</option><option value="cue">Cue</option>
            </select></label>
            <label>Timestamp (ms)<input type="number" min="0" value={eventTimestamp} onChange={event => setEventTimestamp(event.target.value)} /></label>
            <label>Cast member<select value={eventInstanceId} onChange={event => setEventInstanceId(event.target.value)}><option value="">Scene-level event</option>{takeRun?.cast_members.map(item => <option key={item.id} value={item.id}>{item.character_name_snapshot}</option>)}</select></label>
            <label>Payload (JSON)<textarea rows={3} value={eventPayload} onChange={event => setEventPayload(event.target.value)} /></label>
            <button className="secondary-button" disabled={busy || !eventType.trim()}><Plus size={12} /> Record event</button>
            <label>Take duration (ms)<input type="number" min="0" value={durationInput} onChange={event => setDurationInput(event.target.value)} /></label>
            <button type="button" className="primary-button" disabled={busy} onClick={finalizeTake}><Check size={13}/> Finalize take</button>
          </form>}
          <div className="take-event-list">{selectedTake.events.map(item => <div key={item.id}><small>{item.timestamp_ms} ms · #{item.sequence_number}</small><strong>{item.event_type}</strong><code>{JSON.stringify(item.payload)}</code></div>)}</div>
          {writable && selectedTake.status === "finalized" && <button className="primary-button" disabled={busy} onClick={() => chooseTake(selectedTake)}><Check size={13} /> Select take</button>}
        </>}
        {!selectedTake && <p className="muted-note">Start a scene run, then start a take. Append ordered events and finalize it before selecting it for editing.</p>}
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
          {writable && selectedTake?.status === "selected" && !!selectedTake.duration_ms && <button className="secondary-button" disabled={busy || selectedSequence.status !== "draft"} onClick={addSelectedTake}><Plus size={12} /> Add selected take to timeline</button>}
          <div className="edit-timeline">
            {selectedSequence.items.length === 0 && <p className="muted-note">Select a finalized take and add it to this sequence.</p>}
            {[...selectedSequence.items].sort((a,b) => a.item_order-b.item_order).map(item => {
              const take = takes.find(row => row.id === item.take_id);
              const scene = scenes.find(row => row.id === item.scene_id);
              return <article className="edit-timeline-item" key={item.id}>
                <div className="edit-timeline-title"><small>CLIP {item.item_order.toString().padStart(2,"0")} · {item.transition}</small><strong>{scene?.title || "Scene"} · Take {take?.take_number}</strong><span>{item.in_ms}–{item.out_ms} ms · {item.out_ms-item.in_ms} ms</span></div>
                <div className="edit-item-order-controls"><button type="button" aria-label="Move clip up" disabled={!writable || item.item_order===1 || busy} onClick={() => moveItem(item,-1)}><ChevronUp size={14}/></button><button type="button" aria-label="Move clip down" disabled={!writable || item.item_order===selectedSequence.items.length || busy} onClick={() => moveItem(item,1)}><ChevronDown size={14}/></button></div>
                {writable && <div className="edit-item-editor">
                  <label>In (ms)<input type="number" min="0" value={itemDrafts[item.id]?.in_ms ?? String(item.in_ms)} onChange={event => setItemDrafts(current => ({ ...current, [item.id]: { ...(current[item.id] || { in_ms: String(item.in_ms), out_ms: String(item.out_ms), transition: item.transition as EditItemDraft["transition"], title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue }), in_ms: event.target.value } }))}/></label>
                  <label>Out (ms)<input type="number" min="1" value={itemDrafts[item.id]?.out_ms ?? String(item.out_ms)} onChange={event => setItemDrafts(current => ({ ...current, [item.id]: { ...(current[item.id] || { in_ms: String(item.in_ms), out_ms: String(item.out_ms), transition: item.transition as EditItemDraft["transition"], title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue }), out_ms: event.target.value } }))}/></label>
                  <label>Transition<select value={itemDrafts[item.id]?.transition ?? item.transition} onChange={event => setItemDrafts(current => ({ ...current, [item.id]: { ...(current[item.id] || { in_ms: String(item.in_ms), out_ms: String(item.out_ms), transition: item.transition as EditItemDraft["transition"], title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue }), transition: event.target.value as EditItemDraft["transition"] } }))}><option value="cut">Cut</option><option value="fade">Fade</option><option value="dissolve">Dissolve</option></select></label>
                  <label>Title overlay<input value={itemDrafts[item.id]?.title_overlay ?? item.title_overlay} onChange={event => setItemDrafts(current => ({ ...current, [item.id]: { ...(current[item.id] || { in_ms: String(item.in_ms), out_ms: String(item.out_ms), transition: item.transition as EditItemDraft["transition"], title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue }), title_overlay: event.target.value } }))}/></label>
                  <label>Effects (JSON)<input value={itemDrafts[item.id]?.effects ?? JSON.stringify(item.effects)} onChange={event => setItemDrafts(current => ({ ...current, [item.id]: { ...(current[item.id] || { in_ms: String(item.in_ms), out_ms: String(item.out_ms), transition: item.transition as EditItemDraft["transition"], title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue }), effects: event.target.value } }))}/></label>
                  <label>Audio cue<input value={itemDrafts[item.id]?.audio_cue ?? item.audio_cue} onChange={event => setItemDrafts(current => ({ ...current, [item.id]: { ...(current[item.id] || { in_ms: String(item.in_ms), out_ms: String(item.out_ms), transition: item.transition as EditItemDraft["transition"], title_overlay: item.title_overlay, effects: JSON.stringify(item.effects), audio_cue: item.audio_cue }), audio_cue: event.target.value } }))}/></label>
                  <div className="edit-item-actions"><button type="button" className="secondary-button" disabled={busy} onClick={() => saveEditItem(item)}><Save size={12}/> Save clip</button><button type="button" className="quiet-button" disabled={busy} onClick={() => deleteEditItem(item)}>Remove clip</button></div>
                </div>}
              </article>;
            })}
          </div>
          {writable && selectedSequence.items.length > 0 && <button className="primary-button" disabled={busy} onClick={exportSequence}><Download size={13} /> Export edit decision list</button>}
          {exportManifest && <p className="muted-note">Last export: {exportManifest.duration_ms} ms · {exportManifest.clips?.length || 0} clips. Manifest downloaded as JSON.</p>}
          <p className="muted-note">The timeline references immutable selected takes. Trims, transitions, title overlays, effects and audio cues are edit instructions; source performances remain unchanged.</p>
          <AudioTimeline
            projectId={projectId}
            sequenceId={selectedSequence.id}
            editable={writable && selectedSequence.status === "draft"}
            videoDurationMs={selectedSequence.items.reduce((total, item) => total + item.out_ms - item.in_ms, 0)}
          />
          <ProductionVideoExport
            projectId={projectId}
            sequenceId={selectedSequence.id}
            sequenceName={selectedSequence.name}
            sequenceRevision={selectedSequence.revision_number}
            items={selectedSequence.items}
            scenes={scenes}
          />
        </>}
      </section>
    </div>
  </section>;
}
