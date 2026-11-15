import { FormEvent, useEffect, useMemo, useState } from "react";
import { Bot, Clapperboard, Plus, Save, UserRound, Users } from "lucide-react";

type ProjectCharacter = { id: string; name: string; description: string; status: string };
type Member = { id: string; display_name: string | null; email: string | null; role: string; status: string };
type Actor = { id: string; display_name: string; biography: string; performance_notes: string; status: string };
type ControllerType = "user" | "ai_agent" | "script_engine" | "system";
type ControlMode = "direct" | "command" | "assisted" | "autonomous" | "scripted";
type Casting = {
  id: string; actor_id: string; actor_name: string; character_id: string; character_name: string;
  role_label: string; status: "active" | "ended" | "replaced"; controller_type: ControllerType;
  controller_user_id: string | null; control_mode: ControlMode; control_settings: Record<string, unknown>;
};
type Settings = {
  default_controller_type: ControllerType; default_control_mode: ControlMode;
  allow_actor_reuse: boolean; allow_character_recasting: boolean;
};
type Props = {
  projectId: string; phase: string; characters: ProjectCharacter[]; members: Member[];
  currentUserId: string | null; canManage: boolean;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const controllerLabels: Record<ControllerType, string> = {
  user: "Human performer", ai_agent: "AI agent", script_engine: "Script engine", system: "System",
};
const modeLabels: Record<ControlMode, string> = {
  direct: "Direct", command: "Command", assisted: "Assisted", autonomous: "Autonomous", scripted: "Scripted",
};

export default function CastingWorkspace({ projectId, phase, characters, members, currentUserId, canManage }: Props) {
  const [actors, setActors] = useState<Actor[]>([]);
  const [casting, setCasting] = useState<Casting[]>([]);
  const [settings, setSettings] = useState<Settings>({
    default_controller_type: "user", default_control_mode: "direct",
    allow_actor_reuse: true, allow_character_recasting: true,
  });
  const [name, setName] = useState("");
  const [biography, setBiography] = useState("");
  const [performanceNotes, setPerformanceNotes] = useState("");
  const [selectedActors, setSelectedActors] = useState<Record<string, string>>({});
  const [roleLabels, setRoleLabels] = useState<Record<string, string>>({});
  const [controlDrafts, setControlDrafts] = useState<Record<string, { controller_type: ControllerType; control_mode: ControlMode }>>({});
  const [actorDrafts, setActorDrafts] = useState<Record<string, { display_name: string; biography: string; performance_notes: string }>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    const [actorRows, castRows, prefs] = await Promise.all([
      request<Actor[]>("/api/actors"),
      request<Casting[]>(`/api/projects/${projectId}/casting`),
      request<Settings>(`/api/projects/${projectId}/performance-settings`),
    ]);
    setActors(actorRows);
    setCasting(castRows);
    setSettings(prefs);
    setControlDrafts(Object.fromEntries(castRows.filter(item => item.status === "active").map(item => [
      item.id, { controller_type: item.controller_type, control_mode: item.control_mode },
    ])));
    setActorDrafts(Object.fromEntries(actorRows.map(item => [item.id, {
      display_name: item.display_name, biography: item.biography, performance_notes: item.performance_notes,
    }])));
  }

  useEffect(() => {
    let alive = true;
    Promise.all([
      request<Actor[]>("/api/actors"),
      request<Casting[]>(`/api/projects/${projectId}/casting`),
      request<Settings>(`/api/projects/${projectId}/performance-settings`),
    ]).then(([actorRows, castRows, prefs]) => {
      if (!alive) return;
      setActors(actorRows); setCasting(castRows); setSettings(prefs);
      setControlDrafts(Object.fromEntries(castRows.filter(item => item.status === "active").map(item => [
        item.id, { controller_type: item.controller_type, control_mode: item.control_mode },
      ])));
      setActorDrafts(Object.fromEntries(actorRows.map(item => [item.id, {
        display_name: item.display_name, biography: item.biography, performance_notes: item.performance_notes,
      }])));
    }).catch(err => { if (alive) setError(err instanceof Error ? err.message : "Could not load casting workspace."); });
    return () => { alive = false; };
  }, [projectId]);

  const activeCharacters = useMemo(() => characters.filter(item => item.status === "active"), [characters]);
  const activeCasting = casting.filter(item => item.status === "active");
  const castCharacterIds = new Set(activeCasting.map(item => item.character_id));
  const uncastCharacters = activeCharacters.filter(item => !castCharacterIds.has(item.id));
  const activeActors = actors.filter(item => item.status === "active");
  const canCast = canManage && (phase === "storyboard" || phase === "production");

  async function run(action: () => Promise<void>, success: string) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); setNotice(success); }
    catch (err) { setError(err instanceof Error ? err.message : "The change could not be saved."); }
    finally { setBusy(false); }
  }

  async function createActor(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await run(async () => {
      const created = await request<Actor>("/api/actors", {
        method: "POST", body: JSON.stringify({ display_name: name, biography, performance_notes: performanceNotes }),
      });
      setActors(current => [created, ...current]);
      setActorDrafts(current => ({ ...current, [created.id]: { display_name: created.display_name, biography: created.biography, performance_notes: created.performance_notes } }));
      setName(""); setBiography(""); setPerformanceNotes("");
    }, "Actor profile created.");
  }

  async function saveActor(actor: Actor) {
    const draft = actorDrafts[actor.id];
    await run(async () => {
      const updated = await request<Actor>(`/api/actors/${actor.id}`, { method: "PATCH", body: JSON.stringify(draft) });
      setActors(current => current.map(item => item.id === updated.id ? updated : item));
    }, "Actor profile updated.");
  }

  async function archiveActor(actor: Actor) {
    if (!window.confirm(`Archive ${actor.display_name}? This cannot be done while the actor has active cast assignments.`)) return;
    await run(async () => {
      const updated = await request<Actor>(`/api/actors/${actor.id}`, { method: "PATCH", body: JSON.stringify({ status: "archived" }) });
      setActors(current => current.map(item => item.id === updated.id ? updated : item));
    }, "Actor archived.");
  }

  async function assign(character: ProjectCharacter) {
    const actorId = selectedActors[character.id];
    if (!actorId) return;
    await run(async () => {
      await request<Casting>(`/api/projects/${projectId}/casting`, {
        method: "POST", body: JSON.stringify({
          actor_id: actorId, character_id: character.id,
          role_label: roleLabels[character.id]?.trim() || "Cast",
        }),
      });
      await load();
    }, `Cast updated for ${character.name}.`);
  }

  async function saveControl(item: Casting) {
    const draft = controlDrafts[item.id];
    if (!draft) return;
    await run(async () => {
      const updated = await request<Casting>(`/api/projects/${projectId}/casting/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          controller_type: draft.controller_type,
          controller_user_id: draft.controller_type === "user" ? (item.controller_user_id || currentUserId) : null,
          control_mode: draft.control_mode,
        }),
      });
      setCasting(current => current.map(row => row.id === updated.id ? updated : row));
    }, "Controller configuration saved.");
  }

  async function saveSettings(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const updated = await request<Settings>(`/api/projects/${projectId}/performance-settings`, {
        method: "PATCH", body: JSON.stringify(settings),
      });
      setSettings(updated);
    }, "Project performance defaults saved.");
  }

  const controllerSummary = (item: Casting) => item.controller_type === "user"
    ? (item.controller_user_id === currentUserId ? "Assigned to you" : "Human performer")
    : controllerLabels[item.controller_type];

  return (
    <section className="casting-workspace">
      <div className="section-heading contribution-heading">
        <div><div className="section-kicker">M2.0.1 · PERFORMANCE SETUP</div><h2>Cast & performance</h2></div>
        <span className="step-count">{activeCasting.length} active roles · {uncastCharacters.length} uncast</span>
      </div>
      <p className="casting-intro">Actors are performers; characters are roles in this production. Casting connects the two. Controller settings independently determine who or what performs the role.</p>
      {error && <div className="casting-alert error">{error}</div>}
      {notice && <div className="casting-alert success">{notice}</div>}
      {!canCast && <div className="casting-alert">{phase === "development" ? "Casting opens when the project enters storyboarding." : "Casting is read-only for your project role."}</div>}

      <div className="casting-summary-grid">
        <div><strong>{activeCharacters.length}</strong><span>Active characters</span></div>
        <div><strong>{activeCasting.length}</strong><span>Cast assignments</span></div>
        <div><strong>{uncastCharacters.length}</strong><span>Awaiting casting</span></div>
        <div><strong>{activeCasting.filter(item => item.controller_type === "ai_agent").length}</strong><span>AI-controlled</span></div>
      </div>

      <div className="casting-columns">
        <section className="casting-panel">
          <div className="casting-panel-heading"><div><div className="section-kicker">TALENT LIBRARY</div><h3>Your actor profiles</h3></div><span>{actors.length}</span></div>
          {canManage && <form className="casting-form" onSubmit={createActor}>
            <label>Performer name<input required maxLength={160} value={name} onChange={event => setName(event.target.value)} placeholder="e.g. Alex Morgan" /></label>
            <label>Biography<textarea rows={2} maxLength={10000} value={biography} onChange={event => setBiography(event.target.value)} placeholder="A short performer biography" /></label>
            <label>Performance notes<textarea rows={2} maxLength={10000} value={performanceNotes} onChange={event => setPerformanceNotes(event.target.value)} placeholder="Voice, style, strengths or direction notes" /></label>
            <button className="primary-button" disabled={busy || !name.trim()}><Plus size={14} /> Create actor profile</button>
          </form>}
          <div className="casting-actor-list">
            {actors.length === 0 && <p className="muted-note">Your talent library is empty. Create an actor profile to begin casting.</p>}
            {actors.map(actor => {
              const draft = actorDrafts[actor.id] || { display_name: actor.display_name, biography: actor.biography, performance_notes: actor.performance_notes };
              const inUse = activeCasting.some(item => item.actor_id === actor.id);
              return <article className="casting-actor-card" key={actor.id}>
                <div className="casting-actor-title"><UserRound size={15} /><strong>{actor.display_name}</strong><span className={actor.status === "active" ? "status-tag active" : "status-tag"}>{actor.status}</span></div>
                {canManage && actor.status === "active" ? <>
                  <details><summary>Edit profile</summary><div className="casting-form">
                    <label>Name<input value={draft.display_name} onChange={event => setActorDrafts(current => ({ ...current, [actor.id]: { ...draft, display_name: event.target.value } }))} /></label>
                    <label>Biography<textarea rows={2} value={draft.biography} onChange={event => setActorDrafts(current => ({ ...current, [actor.id]: { ...draft, biography: event.target.value } }))} /></label>
                    <label>Performance notes<textarea rows={2} value={draft.performance_notes} onChange={event => setActorDrafts(current => ({ ...current, [actor.id]: { ...draft, performance_notes: event.target.value } }))} /></label>
                    <button type="button" className="secondary-button" disabled={busy || !draft.display_name.trim()} onClick={() => saveActor(actor)}><Save size={13} /> Save profile</button>
                  </div></details>
                  <button type="button" className="quiet-button" disabled={busy || inUse} onClick={() => archiveActor(actor)}>Archive profile</button>
                </> : <p>{actor.biography || "No biography added."}</p>}
              </article>;
            })}
          </div>
        </section>

        <section className="casting-panel production-cast-panel">
          <div className="casting-panel-heading"><div><div className="section-kicker">PRODUCTION CAST</div><h3>Characters & performers</h3></div><Clapperboard size={17} /></div>
          {uncastCharacters.length > 0 && <div className="uncast-list">
            <div className="section-kicker">AWAITING CASTING</div>
            {uncastCharacters.map(character => <div className="uncast-row" key={character.id}>
              <div><strong>{character.name}</strong><small>{character.description || "No character description"}</small></div>
              {canCast && <div className="cast-action">
                <select aria-label={`Actor for ${character.name}`} value={selectedActors[character.id] || ""} onChange={event => setSelectedActors(current => ({ ...current, [character.id]: event.target.value }))}>
                  <option value="">Choose actor</option>{activeActors.map(actor => <option key={actor.id} value={actor.id}>{actor.display_name}</option>)}
                </select>
                <input aria-label={`Role label for ${character.name}`} value={roleLabels[character.id] || ""} onChange={event => setRoleLabels(current => ({ ...current, [character.id]: event.target.value }))} placeholder="Role label (optional)" />
                <button className="secondary-button" disabled={busy || !selectedActors[character.id]} onClick={() => assign(character)}>Cast</button>
              </div>}
            </div>)}
            {activeActors.length === 0 && <p className="muted-note">Create an active actor profile before casting.</p>}
          </div>}
          <div className="active-cast-list">
            <div className="section-kicker">ACTIVE CAST · {activeCasting.length}</div>
            {activeCasting.length === 0 && <p className="muted-note">No characters have been cast yet.</p>}
            {activeCasting.map(item => {
              const draft = controlDrafts[item.id] || { controller_type: item.controller_type, control_mode: item.control_mode };
              return <article className="casting-assignment-card" key={item.id}>
                <div className="casting-assignment-heading"><div><strong>{item.character_name}</strong><span>{item.actor_name}{item.role_label ? ` · ${item.role_label}` : ""}</span></div><span className="status-tag active">Cast</span></div>
                <div className="casting-control-grid">
                  <label>Controller<select disabled={!canManage} value={draft.controller_type} onChange={event => setControlDrafts(current => ({ ...current, [item.id]: { ...draft, controller_type: event.target.value as ControllerType } }))}>
                    <option value="user">Human performer</option><option value="ai_agent">AI agent</option><option value="script_engine">Script engine</option><option value="system">System</option>
                  </select></label>
                  <label>Control mode<select disabled={!canManage} value={draft.control_mode} onChange={event => setControlDrafts(current => ({ ...current, [item.id]: { ...draft, control_mode: event.target.value as ControlMode } }))}>
                    {Object.entries(modeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select></label>
                </div>
                <div className="casting-assignment-footer"><span><Bot size={12} /> {controllerSummary(item)} · {modeLabels[item.control_mode]}</span>
                  {canManage && <button className="quiet-button" disabled={busy || (draft.controller_type === item.controller_type && draft.control_mode === item.control_mode)} onClick={() => saveControl(item)}><Save size={12} /> Save control</button>}
                </div>
                {canCast && <div className="casting-replace-row">
                  <select aria-label={`Replace actor for ${item.character_name}`} value={selectedActors[item.character_id] || ""} onChange={event => setSelectedActors(current => ({ ...current, [item.character_id]: event.target.value }))}>
                    <option value="">Replace performer…</option>
                    {activeActors.filter(actor => settings.allow_actor_reuse || actor.id === item.actor_id || !activeCasting.some(other => other.actor_id === actor.id && other.id !== item.id)).map(actor => <option key={actor.id} value={actor.id}>{actor.display_name}</option>)}
                  </select>
                  <button type="button" className="quiet-button" disabled={busy || !selectedActors[item.character_id] || selectedActors[item.character_id] === item.actor_id} onClick={() => assign({ id: item.character_id, name: item.character_name, description: "", status: "active" })}>Replace cast</button>
                </div>}
              </article>;
            })}
          </div>
          {casting.some(item => item.status !== "active") && <details className="casting-history"><summary>Previous casting history ({casting.filter(item => item.status !== "active").length})</summary>
            {casting.filter(item => item.status !== "active").map(item => <div key={item.id}><strong>{item.character_name}</strong><span>{item.actor_name} · {item.status}</span></div>)}
          </details>}
        </section>
      </div>

      <form className="casting-settings-panel" onSubmit={saveSettings}>
        <div className="casting-panel-heading"><div><div className="section-kicker">PROJECT-WIDE DEFAULTS</div><h3>Performance policy</h3></div><Users size={17} /></div>
        <div className="casting-settings-grid">
          <label>Default controller<select disabled={!canManage} value={settings.default_controller_type} onChange={event => setSettings(current => ({ ...current, default_controller_type: event.target.value as ControllerType }))}>
            {Object.entries(controllerLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          <label>Default control mode<select disabled={!canManage} value={settings.default_control_mode} onChange={event => setSettings(current => ({ ...current, default_control_mode: event.target.value as ControlMode }))}>
            {Object.entries(modeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
        </div>
        <div className="casting-policy-options">
          <label><input type="checkbox" disabled={!canManage} checked={settings.allow_actor_reuse} onChange={event => setSettings(current => ({ ...current, allow_actor_reuse: event.target.checked }))} /> Allow one actor to portray multiple characters</label>
          <label><input type="checkbox" disabled={!canManage} checked={settings.allow_character_recasting} onChange={event => setSettings(current => ({ ...current, allow_character_recasting: event.target.checked }))} /> Allow replacing an existing cast assignment</label>
        </div>
        {canManage && <button className="secondary-button" disabled={busy}><Save size={13} /> Save performance policy</button>}
        <p className="muted-note">Casting and control are deliberately independent. Assigning an actor never grants that actor control of the character; controller and control mode are configured separately.</p>
      </form>
    </section>
  );
}
