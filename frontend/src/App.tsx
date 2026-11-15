import { FormEvent, useEffect, useState } from "react";
import {
  ArrowLeft, ArrowUpRight, BookOpen, CheckCircle2, Clapperboard, Compass,
  Film, Lightbulb, Plus, Sparkles, Users, FolderOpen, LoaderCircle,
} from "lucide-react";

type ApiHealth = { status: string; service: string; version: string };
type Project = {
  id: string; title: string; description: string; logline: string; genre: string;
  visibility: string; current_phase: string; owner_user_id: string;
  created_at: string; updated_at: string; member_count: number;
};
type Member = {
  id: string; display_name: string | null; email: string | null;
  invited_email: string | null; role: string; status: string; created_at: string;
};
type ProjectDetail = Project & { members: Member[] };
type ProjectForm = { title: string; logline: string; genre: string; description: string; visibility: string };

const phases = [
  { number: "01", title: "Story contributions", detail: "Bring your first ideas to the table.", icon: BookOpen, state: "active" },
  { number: "02", title: "Develop the story", detail: "Discuss, combine and shape the narrative.", icon: Lightbulb, state: "upcoming" },
  { number: "03", title: "Storyboard", detail: "Turn the story into scenes.", icon: Clapperboard, state: "upcoming" },
  { number: "04", title: "Bring it to life", detail: "Cast, perform, direct and edit.", icon: Film, state: "upcoming" },
];

const emptyForm: ProjectForm = { title: "", logline: "", genre: "", description: "", visibility: "private" };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
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

function App() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [apiError, setApiError] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [view, setView] = useState<"overview" | "projects" | "detail">("overview");
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<ProjectForm>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("contributor");
  const [inviteMessage, setInviteMessage] = useState("");

  async function loadProjects() {
    const data = await api<Project[]>("/api/projects");
    setProjects(data);
  }

  useEffect(() => {
    api<ApiHealth>("/api/health").then(setHealth).catch(() => setApiError(true));
    loadProjects().catch((err: Error) => setError(err.message));
  }, []);

  async function openProject(projectId: string) {
    setLoading(true);
    setError("");
    try {
      const detail = await api<ProjectDetail>(`/api/projects/${projectId}`);
      setSelectedProject(detail);
      setView("detail");
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open project.");
    } finally {
      setLoading(false);
    }
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const created = await api<Project>("/api/projects", {
        method: "POST", body: JSON.stringify(form),
      });
      await loadProjects();
      setForm(emptyForm);
      setShowCreate(false);
      await openProject(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create project.");
    } finally {
      setLoading(false);
    }
  }

  async function inviteMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject) return;
    setInviteMessage("");
    setError("");
    try {
      await api<Member>(`/api/projects/${selectedProject.id}/invitations`, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      const updated = await api<ProjectDetail>(`/api/projects/${selectedProject.id}`);
      setSelectedProject(updated);
      setInviteEmail("");
      setInviteMessage("Invitation recorded. Email delivery and account acceptance will be added with authentication.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not invite member.");
    }
  }

  function showProjects() {
    setView("projects");
    setSelectedProject(null);
    setShowCreate(false);
    setError("");
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="StoryForge home" onClick={() => setView("overview")}>
          <span className="brand-mark"><Sparkles size={20} /></span>
          <span className="brand-name">storyforge<span>.</span></span>
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <button className={view === "overview" ? "nav-item selected" : "nav-item"} onClick={() => setView("overview")}><Compass size={17} /> Overview</button>
          <button className={view !== "overview" ? "nav-item selected" : "nav-item"} onClick={showProjects}><BookOpen size={17} /> My projects <span className="nav-count">{projects.length}</span></button>
          <button className="nav-item" onClick={showProjects}><Users size={17} /> Community</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="collective-card">
            <div className="collective-icon"><Sparkles size={16} /></div>
            <div><strong>The StoryForge Collective</strong><span>Many minds. Many stories.</span></div>
          </div>
          <div className="profile-row">
            <div className="avatar">S</div>
            <div className="profile-copy"><strong>Storyteller</strong><span>Local development account</span></div>
            <span className="profile-dots">···</span>
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> {view === "overview" ? "Overview" : view === "detail" ? selectedProject?.title || "Project" : "My projects"}</div>
          <div className="topbar-right"><span className="beta-pill">EARLY ACCESS</span><div className="avatar small">S</div></div>
        </header>

        <div className="content">
          {view === "overview" && (
            <>
              <section className="welcome">
                <div className="eyebrow"><span className="eyebrow-line" /> THE CREATIVE COLLECTIVE</div>
                <h1>Every great story<br /><em>starts together.</em></h1>
                <p className="welcome-copy">A space to bring ideas together, build worlds with others, and turn shared stories into something worth watching.</p>
                <div className="welcome-actions">
                  <button className="primary-button" type="button" onClick={() => { setView("projects"); setShowCreate(true); }}><Plus size={17} /> Create a project</button>
                  <button className="text-link button-link" type="button" onClick={() => document.getElementById("journey")?.scrollIntoView({ behavior: "smooth" })}>Explore the process <ArrowUpRight size={15} /></button>
                </div>
              </section>
              <section className="journey-section" id="journey">
                <div className="section-heading">
                  <div><div className="section-kicker">HOW IT WORKS</div><h2>From first thought to final frame.</h2></div>
                  <span className="step-count">A creative journey <span>·</span> 4 stages</span>
                </div>
                <div className="phase-grid">
                  {phases.map((phase) => {
                    const Icon = phase.icon;
                    return <article className={`phase-card ${phase.state}`} key={phase.number}>
                      <div className="phase-top"><span>{phase.number}</span><Icon size={19} /></div>
                      <h3>{phase.title}</h3><p>{phase.detail}</p>
                      <div className="phase-status">{phase.state === "active" ? <><span className="status-dot" /> FIRST MILESTONE</> : "ON THE ROADMAP"}</div>
                    </article>;
                  })}
                </div>
              </section>
              <section className="bottom-grid">
                <div className="note-card"><div className="note-icon"><Sparkles size={18} /></div><div><div className="section-kicker">THE IDEA</div><h3>Many minds. Many stories. Endless interpretations.</h3><p>One shared starting point can lead to a hundred different creative directions. That's the heart of StoryForge.</p></div></div>
                <div className="connection-card">
                  <div className="connection-heading"><span className={health ? "connection-light online" : "connection-light"} /> DEVELOPMENT STATUS</div>
                  <strong>{health ? "Backend connected" : apiError ? "Backend unavailable" : "Connecting to backend…"}</strong>
                  <p>{health ? `${health.service} · v${health.version}` : apiError ? "Start the Docker services to connect the application." : "Checking the StoryForge API."}</p>
                  {health && <div className="connected-label"><CheckCircle2 size={14} /> All systems operational</div>}
                </div>
              </section>
            </>
          )}

          {view === "projects" && (
            <section className="workspace-view">
              <div className="view-heading">
                <div><div className="section-kicker">YOUR CREATIVE WORKSPACE</div><h1>My <em>projects.</em></h1><p>Stories you're creating, developing and bringing to life.</p></div>
                <button className="primary-button" onClick={() => { setShowCreate(!showCreate); setError(""); }}><Plus size={17} /> New project</button>
              </div>
              {error && <div className="error-banner">{error}</div>}
              {showCreate && (
                <form className="project-form" onSubmit={createProject}>
                  <div className="form-title"><div><div className="section-kicker">A NEW COLLABORATION</div><h2>Start with an idea.</h2></div><button type="button" className="quiet-button" onClick={() => setShowCreate(false)}>Cancel</button></div>
                  <label>Project title<input autoFocus required maxLength={160} placeholder="Give your story a working title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
                  <label>Logline <span className="field-hint">A one-sentence hook (optional)</span><input maxLength={500} placeholder="What's the story about?" value={form.logline} onChange={e => setForm({ ...form, logline: e.target.value })} /></label>
                  <div className="form-row">
                    <label>Genre<input maxLength={80} placeholder="e.g. Sci-fi, drama, fantasy" value={form.genre} onChange={e => setForm({ ...form, genre: e.target.value })} /></label>
                    <label>Visibility<select value={form.visibility} onChange={e => setForm({ ...form, visibility: e.target.value })}><option value="private">Private · members only</option><option value="unlisted">Unlisted · link access later</option><option value="public">Public · discoverable later</option></select></label>
                  </div>
                  <label>Project description<textarea rows={3} maxLength={10000} placeholder="Set the scene. What do you want to make together?" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
                  <div className="form-actions"><span>You'll be the project owner. You can invite collaborators next.</span><button className="primary-button" disabled={loading} type="submit">{loading ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />} Create project</button></div>
                </form>
              )}
              {!showCreate && projects.length === 0 && (
                <div className="empty-state"><div className="empty-icon"><FolderOpen size={25} /></div><h2>Your first story starts here.</h2><p>Create a project to give your ideas a home. You can invite collaborators as the story takes shape.</p><button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={16} /> Create your first project</button></div>
              )}
              {projects.length > 0 && <div className="project-grid">{projects.map(project => (
                <button className="project-card" key={project.id} onClick={() => openProject(project.id)}>
                  <div className="project-card-top"><span className="project-genre">{project.genre || "Untitled genre"}</span><span className="project-visibility">{project.visibility}</span></div>
                  <h2>{project.title}</h2><p>{project.logline || project.description || "A new story is waiting to be told."}</p>
                  <div className="project-card-bottom"><span><Users size={14} /> {project.member_count} {project.member_count === 1 ? "member" : "members"}</span><span>Contributions <ArrowUpRight size={14} /></span></div>
                </button>
              ))}</div>}
            </section>
          )}

          {view === "detail" && selectedProject && (
            <section className="workspace-view">
              <button className="back-button" onClick={showProjects}><ArrowLeft size={15} /> All projects</button>
              {error && <div className="error-banner">{error}</div>}
              <div className="detail-hero">
                <div className="eyebrow"><span className="eyebrow-line" /> PROJECT WORKSPACE</div>
                <div className="detail-meta"><span>{selectedProject.genre || "Story project"}</span><span>{selectedProject.visibility}</span><span>Created {new Date(selectedProject.created_at).toLocaleDateString()}</span></div>
                <h1>{selectedProject.title}</h1>
                {selectedProject.logline && <p className="detail-logline">{selectedProject.logline}</p>}
                {selectedProject.description && <p className="detail-description">{selectedProject.description}</p>}
              </div>
              <div className="detail-columns">
                <div className="detail-panel"><div className="section-kicker">CURRENT STAGE</div><h2>Story contributions</h2><p>This is the starting point for the project. The next milestone will let each participant submit an independent story contribution.</p><span className="stage-pill"><span className="status-dot" /> IN PROGRESS</span></div>
                <div className="detail-panel members-panel"><div className="panel-heading"><div><div className="section-kicker">THE CREATIVE TEAM</div><h2>Members <span>{selectedProject.members.length}</span></h2></div></div>
                  <div className="member-list">{selectedProject.members.map(member => <div className="member-row" key={member.id}><div className="avatar">{(member.display_name || member.invited_email || "?").charAt(0).toUpperCase()}</div><div className="member-copy"><strong>{member.display_name || member.invited_email}</strong><span>{member.email || (member.status === "invited" ? "Invitation pending" : "")}</span></div><span className={member.status === "invited" ? "role-tag pending" : "role-tag"}>{member.role}</span></div>)}</div>
                  <form className="invite-form" onSubmit={inviteMember}><div className="section-kicker">INVITE A COLLABORATOR</div><input type="email" required placeholder="Email address" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} /><div className="invite-controls"><select value={inviteRole} onChange={e => setInviteRole(e.target.value)}><option value="contributor">Contributor</option><option value="editor">Editor</option><option value="viewer">Viewer</option></select><button className="primary-button" type="submit"><Plus size={15} /> Invite</button></div>{inviteMessage && <p className="success-message">{inviteMessage}</p>}</form>
                </div>
              </div>
            </section>
          )}
          <footer className="footer"><span>STORYFORGE COLLECTIVE</span><span>Built together, one story at a time.</span></footer>
        </div>
      </section>
    </main>
  );
}

export default App;
