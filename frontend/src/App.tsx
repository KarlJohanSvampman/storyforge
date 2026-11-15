import { FormEvent, useEffect, useState } from "react";
import {
  ArrowLeft, ArrowUpRight, BookOpen, CheckCircle2, Clapperboard, Compass,
  Film, Lightbulb, Plus, Sparkles, Users, FolderOpen, LoaderCircle,
  FileText, History, Send, Clock3, RotateCcw, X,
} from "lucide-react";

type ApiHealth = { status: string; service: string; version: string };
type CurrentUser = { id: string; display_name: string; email: string };
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
type Contribution = {
  id: string; project_id: string; author_user_id: string; author_display_name: string;
  title: string; status: string; current_revision_number: number; current_revision_id: string; current_body: string;
  created_at: string; updated_at: string;
};
type ContributionRevision = {
  id: string; revision_number: number; title: string; body: string; author_user_id: string;
  author_display_name: string; created_at: string;
};
type ContributionDetail = Contribution & { revisions: ContributionRevision[] };
type Comment = { id: string; contribution_id: string; revision_id: string | null; parent_comment_id: string | null; author_user_id: string; author_display_name: string; body: string; created_at: string };
type SuggestionDecision = { id: string; actor_user_id: string; actor_display_name: string; previous_status: string | null; new_status: string; note: string; created_at: string };
type Suggestion = { id: string; contribution_id: string; target_revision_id: string; author_user_id: string; author_display_name: string; title: string; rationale: string; proposed_text: string; status: string; created_at: string; updated_at: string; decisions: SuggestionDecision[] };


type DraftSource = {
  id: string; source_order: number; source_kind: string; contribution_id: string;
  contribution_revision_id: string; suggestion_id: string | null;
  source_title: string; source_text_snapshot: string;
};
type DraftVersion = {
  id: string; version_number: number; title: string; content: string; status: string;
  origin: string; provider_name: string | null; model_name: string | null;
  prompt_version: string | null; author_user_id: string; author_display_name: string;
  parent_version_id: string | null; created_at: string; sources: DraftSource[];
};
type NarrativeDraft = {
  id: string; project_id: string; title: string; current_version_number: number;
  created_by_user_id: string; created_at: string; updated_at: string; versions: DraftVersion[];
};


type ApprovalMode = "owner_only" | "majority";
type ApprovalChoice = "approve" | "reject";
type ApprovalVote = {
  id: string; version_id: string; voter_user_id: string; voter_display_name: string;
  choice: ApprovalChoice; note: string; created_at: string;
  is_latest: boolean; counts_toward_result: boolean;
};
type ApprovalDecision = {
  id: string; version_id: string; actor_user_id: string; actor_display_name: string;
  outcome: "approved" | "rejected"; rule_mode: ApprovalMode;
  eligible_voter_count: number; approve_count: number; reject_count: number;
  required_votes: number; note: string; created_at: string;
};
type ApprovalVersion = {
  version_id: string; version_number: number; is_current_version: boolean;
  rule_mode: ApprovalMode; ballot_opened_at: string | null;
  eligible_voter_count: number; required_votes: number; approve_count: number; reject_count: number;
  current_user_vote: ApprovalChoice | null; can_vote: boolean; can_finalize: boolean;
  decision_outcome: "approved" | "rejected" | null;
  votes: ApprovalVote[]; decision: ApprovalDecision | null;
};
type PhaseTransition = {
  id: string; from_phase: string; to_phase: string; actor_user_id: string;
  actor_display_name: string; narrative_version_id: string | null;
  reason: string; created_at: string;
};
type ApprovalOverview = {
  project_id: string; current_phase: string;
  rule: { mode: ApprovalMode; configured: boolean; updated_by_user_id: string | null; updated_at: string | null };
  versions: ApprovalVersion[]; phase_history: PhaseTransition[];
};

type ProjectCharacter = {
  id: string; project_id: string; name: string; description: string;
  visual_description: string; personality_notes: string; status: string;
  created_by_user_id: string; created_at: string; updated_at: string;
};
type ProjectLocation = {
  id: string; project_id: string; name: string; description: string;
  environment_type: string; time_period: string; visual_notes: string; status: string;
  created_by_user_id: string; created_at: string; updated_at: string;
};
type ScenePassage = {
  id: string; reference_order: number; start_offset: number; end_offset: number;
  passage_snapshot: string; created_by_user_id: string; created_at: string;
};
type SceneScriptVersion = {
  id: string; revision_number: number; content: string; parent_version_id: string | null;
  author_user_id: string; author_display_name: string; created_at: string;
};
type SceneCharacter = { id: string; name: string; role_label: string; notes: string };
type StoryboardScene = {
  id: string; scene_order: number; title: string; summary: string; requirements: string;
  estimated_duration_seconds: number | null; location_id: string | null; location_name: string | null;
  characters: SceneCharacter[]; passages: ScenePassage[]; script_versions: SceneScriptVersion[];
  created_by_user_id: string; created_at: string; updated_at: string;
};
type Storyboard = {
  id: string; project_id: string; title: string; narrative_version_id: string;
  narrative_version_number: number; narrative_title: string; narrative_content: string;
  created_by_user_id: string; created_at: string;
  scenes: StoryboardScene[]; characters: ProjectCharacter[]; locations: ProjectLocation[];
};

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
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [view, setView] = useState<"overview" | "projects" | "detail">("overview");
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [selectedContribution, setSelectedContribution] = useState<ContributionDetail | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [acceptedDraftSuggestions, setAcceptedDraftSuggestions] = useState<Suggestion[]>([]);
  const [selectedDraftSuggestionIds, setSelectedDraftSuggestionIds] = useState<string[]>([]);
  const [draft, setDraft] = useState<NarrativeDraft | null>(null);
  const [approval, setApproval] = useState<ApprovalOverview | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [characterName, setCharacterName] = useState("");
  const [characterDescription, setCharacterDescription] = useState("");
  const [characterVisual, setCharacterVisual] = useState("");
  const [characterPersonality, setCharacterPersonality] = useState("");
  const [locationName, setLocationName] = useState("");
  const [locationDescription, setLocationDescription] = useState("");
  const [locationType, setLocationType] = useState("interior");
  const [locationPeriod, setLocationPeriod] = useState("");
  const [locationVisual, setLocationVisual] = useState("");
  const [sceneTitle, setSceneTitle] = useState("");
  const [sceneSummary, setSceneSummary] = useState("");
  const [sceneRequirements, setSceneRequirements] = useState("");
  const [sceneDuration, setSceneDuration] = useState("");
  const [sceneLocationId, setSceneLocationId] = useState("");
  const [sceneCharacterIds, setSceneCharacterIds] = useState<string[]>([]);
  const [scriptDrafts, setScriptDrafts] = useState<Record<string, string>>({});
  const [passageDrafts, setPassageDrafts] = useState<Record<string, string>>({});
  const [passageOccurrences, setPassageOccurrences] = useState<Record<string, string>>({});
  const [approvalMode, setApprovalMode] = useState<ApprovalMode>("owner_only");
  const [approvalNote, setApprovalNote] = useState("");
  const [draftSourceIds, setDraftSourceIds] = useState<string[]>([]);
  const [draftTitle, setDraftTitle] = useState("");
  const [editingDraft, setEditingDraft] = useState(false);
  const [draftEditTitle, setDraftEditTitle] = useState("");
  const [draftEditContent, setDraftEditContent] = useState("");
  const [selectedDraftVersionId, setSelectedDraftVersionId] = useState<string | null>(null);
  const [commentBody, setCommentBody] = useState("");
  const [suggestionTitle, setSuggestionTitle] = useState("");
  const [suggestionRationale, setSuggestionRationale] = useState("");
  const [suggestionText, setSuggestionText] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<ProjectForm>(emptyForm);
  const [contributionTitle, setContributionTitle] = useState("");
  const [contributionBody, setContributionBody] = useState("");
  const [editingContribution, setEditingContribution] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("contributor");
  const [inviteMessage, setInviteMessage] = useState("");

  async function loadProjects() {
    setProjects(await api<Project[]>("/api/projects"));
  }

  async function loadApproval(projectId: string) {
    const result = await api<ApprovalOverview>(`/api/projects/${projectId}/approval`);
    setApproval(result);
    setApprovalMode(result.rule.mode);
    return result;
  }


  async function loadAcceptedDraftSuggestions(projectId: string, items: Contribution[]) {
    const active = items.filter(item => item.status === "active");
    const groups = await Promise.all(active.map(item =>
      api<Suggestion[]>(`/api/projects/${projectId}/contributions/${item.id}/suggestions`)
    ));
    const accepted = groups.flat().filter(suggestion =>
      suggestion.status === "accepted" &&
      active.some(item => item.current_revision_id === suggestion.target_revision_id)
    );
    setAcceptedDraftSuggestions(accepted);
    setSelectedDraftSuggestionIds([]);
  }

  async function loadContributions(projectId: string) {
    const items = await api<Contribution[]>(`/api/projects/${projectId}/contributions`);
    setContributions(items);
    setDraftSourceIds(items.filter(item => item.status === "active").map(item => item.current_revision_id));
    await loadAcceptedDraftSuggestions(projectId, items);
  }

  useEffect(() => {
    api<ApiHealth>("/api/health").then(setHealth).catch(() => setApiError(true));
    api<CurrentUser>("/api/me").then(setCurrentUser).catch(() => undefined);
    loadProjects().catch((err: Error) => setError(err.message));
  }, []);

  async function openProject(projectId: string) {
    setLoading(true);
    setError("");
    try {
      const [detail, items, currentDraft, approvalOverview] = await Promise.all([
        api<ProjectDetail>(`/api/projects/${projectId}`),
        api<Contribution[]>(`/api/projects/${projectId}/contributions`),
        api<NarrativeDraft | null>(`/api/projects/${projectId}/draft`),
        api<ApprovalOverview>(`/api/projects/${projectId}/approval`),
      ]);
      setSelectedProject(detail);
      setContributions(items);
      await loadAcceptedDraftSuggestions(projectId, items);
      setDraft(currentDraft);
      setApproval(approvalOverview);
      setApprovalMode(approvalOverview.rule.mode);
      setApprovalNote("");
      setDraftTitle(currentDraft?.title || detail.title);
      setDraftSourceIds(items.filter(item => item.status === "active").map(item => item.current_revision_id));
      setSelectedDraftVersionId(currentDraft?.versions[currentDraft.versions.length - 1]?.id || null);
      setEditingDraft(false);
      setSelectedContribution(null);
      setContributionTitle("");
      setContributionBody("");
      setEditingContribution(false);
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
        method: "POST", body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      const updated = await api<ProjectDetail>(`/api/projects/${selectedProject.id}`);
      setSelectedProject(updated);
      setInviteEmail("");
      setInviteMessage("Invitation recorded. Email delivery and account acceptance will be added with authentication.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not invite member.");
    }
  }

  async function submitContribution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject) return;
    setLoading(true);
    setError("");
    try {
      if (editingContribution && selectedContribution) {
        await api<Contribution>(`/api/projects/${selectedProject.id}/contributions/${selectedContribution.id}`, {
          method: "PATCH",
          body: JSON.stringify({ title: contributionTitle, body: contributionBody }),
        });
      } else {
        await api<Contribution>(`/api/projects/${selectedProject.id}/contributions`, {
          method: "POST",
          body: JSON.stringify({ title: contributionTitle, body: contributionBody }),
        });
      }
      await loadContributions(selectedProject.id);
      if (selectedContribution) {
        const refreshed = await api<ContributionDetail>(`/api/projects/${selectedProject.id}/contributions/${selectedContribution.id}`);
        setSelectedContribution(refreshed);
      }
      setContributionTitle("");
      setContributionBody("");
      setEditingContribution(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save contribution.");
    } finally {
      setLoading(false);
    }
  }

  async function openContribution(item: Contribution) {
    if (!selectedProject) return;
    setError("");
    try {
      const detail = await api<ContributionDetail>(`/api/projects/${selectedProject.id}/contributions/${item.id}`);
      setSelectedContribution(detail);
      const [commentItems, suggestionItems] = await Promise.all([
        api<Comment[]>("/api/projects/" + selectedProject.id + "/contributions/" + item.id + "/comments"),
        api<Suggestion[]>("/api/projects/" + selectedProject.id + "/contributions/" + item.id + "/suggestions"),
      ]);
      setComments(commentItems);
      setSuggestions(suggestionItems);
      setContributionTitle(detail.title);
      setContributionBody(detail.current_body);
      setEditingContribution(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load contribution.");
    }
  }


  async function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !selectedContribution || !commentBody.trim()) return;
    setError("");
    try {
      const latest = selectedContribution.revisions[selectedContribution.revisions.length - 1];
      const created = await api<Comment>("/api/projects/" + selectedProject.id + "/contributions/" + selectedContribution.id + "/comments", {
        method: "POST", body: JSON.stringify({ body: commentBody, revision_id: latest?.id || null }),
      });
      setComments([...comments, created]); setCommentBody("");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not add comment."); }
  }

  async function submitSuggestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !selectedContribution) return;
    const latest = selectedContribution.revisions[selectedContribution.revisions.length - 1];
    if (!latest) return;
    setError("");
    try {
      const created = await api<Suggestion>("/api/projects/" + selectedProject.id + "/contributions/" + selectedContribution.id + "/suggestions", {
        method: "POST", body: JSON.stringify({ target_revision_id: latest.id, title: suggestionTitle, rationale: suggestionRationale, proposed_text: suggestionText }),
      });
      setSuggestions([...suggestions, created]); setSuggestionTitle(""); setSuggestionRationale(""); setSuggestionText("");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not submit suggestion."); }
  }

  async function decideSuggestion(suggestion: Suggestion, status: "accepted" | "rejected" | "deferred") {
    if (!selectedProject || !selectedContribution) return;
    setError("");
    try {
      const updated = await api<Suggestion>("/api/projects/" + selectedProject.id + "/contributions/" + selectedContribution.id + "/suggestions/" + suggestion.id + "/decision", {
        method: "POST", body: JSON.stringify({ status, note: "" }),
      });
      setSuggestions(suggestions.map(item => item.id === updated.id ? updated : item));
      setAcceptedDraftSuggestions(current => status === "accepted"
        ? [...current.filter(item => item.id !== updated.id), updated]
        : current.filter(item => item.id !== updated.id));
      if (status !== "accepted") {
        setSelectedDraftSuggestionIds(current => current.filter(id => id !== updated.id));
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update suggestion."); }
  }


  async function compileNarrativeDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || draftSourceIds.length === 0) return;
    setLoading(true);
    setError("");
    try {
      const created = await api<NarrativeDraft>(`/api/projects/${selectedProject.id}/draft/compile`, {
        method: "POST",
        body: JSON.stringify({
          title: draftTitle.trim() || selectedProject.title,
          sources: draftSourceIds.map(revision_id => ({
            revision_id,
            accepted_suggestion_ids: acceptedDraftSuggestions
              .filter(suggestion => suggestion.target_revision_id === revision_id && selectedDraftSuggestionIds.includes(suggestion.id))
              .map(suggestion => suggestion.id),
          })),
        }),
      });
      setDraft(created);
      setDraftTitle(created.title);
      setSelectedDraftVersionId(created.versions[created.versions.length - 1]?.id || null);
      await loadApproval(selectedProject.id);
      setEditingDraft(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not compile the narrative draft.");
    } finally {
      setLoading(false);
    }
  }

  function startDraftRevision() {
    const latest = draft?.versions[draft.versions.length - 1];
    if (!latest) return;
    setDraftEditTitle(latest.title);
    setDraftEditContent(latest.content);
    setSelectedDraftVersionId(latest.id);
    setEditingDraft(true);
  }

  async function saveDraftRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !draft) return;
    const latest = draft.versions[draft.versions.length - 1];
    if (!latest) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<NarrativeDraft>(`/api/projects/${selectedProject.id}/draft/${draft.id}/versions`, {
        method: "POST",
        body: JSON.stringify({
          base_version_id: latest.id,
          title: draftEditTitle,
          content: draftEditContent,
        }),
      });
      setDraft(updated);
      setSelectedDraftVersionId(updated.versions[updated.versions.length - 1]?.id || null);
      await loadApproval(selectedProject.id);
      setEditingDraft(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the revised draft.");
    } finally {
      setLoading(false);
    }
  }


  async function saveApprovalRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject) return;
    setError("");
    setLoading(true);
    try {
      const updated = await api<ApprovalOverview>(`/api/projects/${selectedProject.id}/approval-rule`, {
        method: "PUT",
        body: JSON.stringify({ mode: approvalMode }),
      });
      setApproval(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the approval rule.");
    } finally {
      setLoading(false);
    }
  }

  async function castApprovalVote(choice: ApprovalChoice) {
    if (!selectedProject || !draft || !selectedDraftVersion) return;
    setError("");
    setLoading(true);
    try {
      const updated = await api<ApprovalOverview>(
        `/api/projects/${selectedProject.id}/draft/${draft.id}/versions/${selectedDraftVersion.id}/votes`,
        { method: "POST", body: JSON.stringify({ choice, note: approvalNote }) },
      );
      setApproval(updated);
      setApprovalNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record your vote.");
    } finally {
      setLoading(false);
    }
  }

  async function finalizeApprovalDecision() {
    if (!selectedProject || !draft || !selectedDraftVersion) return;
    setError("");
    setLoading(true);
    try {
      const updated = await api<ApprovalOverview>(
        `/api/projects/${selectedProject.id}/draft/${draft.id}/versions/${selectedDraftVersion.id}/decision`,
        { method: "POST", body: JSON.stringify({ note: approvalNote }) },
      );
      setApproval(updated);
      setApprovalNote("");
      setEditingDraft(false);
      const refreshedProject = await api<ProjectDetail>(`/api/projects/${selectedProject.id}`);
      setSelectedProject(refreshedProject);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not finalize the approval decision.");
    } finally {
      setLoading(false);
    }
  }

  function startRevision() {
    if (!selectedContribution) return;
    setContributionTitle(selectedContribution.title);
    setContributionBody(selectedContribution.current_body);
    setEditingContribution(true);
  }

  async function withdrawContribution(item: ContributionDetail) {
    if (!selectedProject || !window.confirm("Withdraw this contribution? Its existing revisions will remain in the project history.")) return;
    setError("");
    try {
      await api<Contribution>(`/api/projects/${selectedProject.id}/contributions/${item.id}/withdraw`, { method: "POST" });
      await loadContributions(selectedProject.id);
      const refreshed = await api<ContributionDetail>(`/api/projects/${selectedProject.id}/contributions/${item.id}`);
      setSelectedContribution(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not withdraw contribution.");
    }
  }

  function showProjects() {
    setView("projects");
    setSelectedProject(null);
    setSelectedContribution(null);
    setShowCreate(false);
    setError("");
  }

  const myMembership = selectedProject?.members.find(member => member.email === currentUser?.email);
  const canContribute = !!myMembership && myMembership.status === "active" && myMembership.role !== "viewer";
  const canReviseSelected = !!selectedContribution && !!currentUser && (
    selectedContribution.author_user_id === currentUser.id || myMembership?.role === "owner" || myMembership?.role === "editor"
  );
  const latestDraftVersion = draft?.versions[draft.versions.length - 1] || null;
  const selectedDraftVersion = draft?.versions.find(version => version.id === selectedDraftVersionId) || latestDraftVersion;
  const selectedApproval = approval?.versions.find(item => item.version_id === selectedDraftVersion?.id) || null;
  const canManageApprovalRule = myMembership?.role === "owner";
  const approvalRuleLocked = !!approval?.versions.some(item => item.votes.length > 0 || item.decision !== null);


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
            <div className="avatar">{(currentUser?.display_name || "S").charAt(0)}</div>
            <div className="profile-copy"><strong>{currentUser?.display_name || "Storyteller"}</strong><span>Local development account</span></div>
            <span className="profile-dots">···</span>
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> {view === "overview" ? "Overview" : view === "detail" ? selectedProject?.title || "Project" : "My projects"}</div>
          <div className="topbar-right"><span className="beta-pill">EARLY ACCESS</span><div className="avatar small">{(currentUser?.display_name || "S").charAt(0)}</div></div>
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
                  {phases.map(phase => {
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
                  <div className="project-card-bottom"><span><Users size={14} /> {project.member_count} {project.member_count === 1 ? "member" : "members"}</span><span>{project.current_phase} <ArrowUpRight size={14} /></span></div>
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
                <div className="detail-panel"><div className="section-kicker">CURRENT STAGE</div><h2>{selectedProject.current_phase === "storyboard" ? "Storyboard" : selectedProject.current_phase === "development" ? "Story development" : selectedProject.current_phase === "production" ? "Production" : selectedProject.current_phase === "published" ? "Published" : "Story contributions"}</h2><p>{selectedProject.current_phase === "storyboard" ? "The narrative has been approved. The project is ready to be broken into scenes and storyboards." : "Contributions remain independent while the group shapes and approves a shared narrative."}</p><span className="stage-pill"><span className="status-dot" /> {selectedProject.current_phase.replace("_", " ").toUpperCase()}</span></div>
                <div className="detail-panel members-panel"><div className="panel-heading"><div><div className="section-kicker">THE CREATIVE TEAM</div><h2>Members <span>{selectedProject.members.length}</span></h2></div></div>
                  <div className="member-list">{selectedProject.members.map(member => <div className="member-row" key={member.id}><div className="avatar">{(member.display_name || member.invited_email || "?").charAt(0).toUpperCase()}</div><div className="member-copy"><strong>{member.display_name || member.invited_email}</strong><span>{member.email || (member.status === "invited" ? "Invitation pending" : "")}</span></div><span className={member.status === "invited" ? "role-tag pending" : "role-tag"}>{member.role}</span></div>)}</div>
                  <form className="invite-form" onSubmit={inviteMember}><div className="section-kicker">INVITE A COLLABORATOR</div><input type="email" required placeholder="Email address" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} /><div className="invite-controls"><select value={inviteRole} onChange={e => setInviteRole(e.target.value)}><option value="contributor">Contributor</option><option value="editor">Editor</option><option value="viewer">Viewer</option></select><button className="primary-button" type="submit"><Plus size={15} /> Invite</button></div>{inviteMessage && <p className="success-message">{inviteMessage}</p>}</form>
                </div>
              </div>


              <section className="drafts-section">
                <div className="section-heading contribution-heading">
                  <div><div className="section-kicker">NARRATIVE DEVELOPMENT</div><h2>Combined story draft</h2></div>
                  <span className="step-count">{draft ? `Version ${draft.current_version_number} · proposal` : "Not compiled yet"}</span>
                </div>
                <p className="muted-note">This first compiler assembles selected text without rewriting it. Every generated version is an unapproved proposal with exact source references; original contributions remain untouched. A real AI provider can replace the mock compiler later.</p>

                <div className="approval-rule-card">
                  <div className="approval-rule-copy">
                    <div className="section-kicker">PROJECT APPROVAL RULE</div>
                    <strong>{approval?.rule.mode === "majority" ? "Majority of active creative members" : "Project owner approval"}</strong>
                    <p>Owner approval requires the owner's vote. Majority requires more than half of active owners, editors and contributors. Viewers and pending invitations do not count.</p>
                  </div>
                  {canManageApprovalRule && (
                    <form className="approval-rule-form" onSubmit={saveApprovalRule}>
                      <label>Decision rule
                        <select value={approvalMode} disabled={approvalRuleLocked || selectedProject.current_phase === "storyboard"} onChange={event => setApprovalMode(event.target.value as ApprovalMode)}>
                          <option value="owner_only">Owner approval</option>
                          <option value="majority">Majority of active creative members</option>
                        </select>
                      </label>
                      <button className="secondary-button" type="submit" disabled={loading || approvalRuleLocked || selectedProject.current_phase === "storyboard"}>Save rule</button>
                      {approvalRuleLocked && <small>Locked because voting has started on a draft version.</small>}
                      {selectedProject.current_phase === "storyboard" && <small>Locked after the approved narrative moved the project into storyboarding.</small>}
                    </form>
                  )}
                </div>

                {canContribute && selectedProject.current_phase !== "storyboard" && (
                  <form className="draft-compile-form" onSubmit={compileNarrativeDraft}>
                    <label>Draft title<input maxLength={160} value={draftTitle} onChange={event => setDraftTitle(event.target.value)} placeholder={selectedProject.title} /></label>
                    <div className="draft-source-picker">
                      <div className="section-kicker">SELECT ACTIVE CONTRIBUTIONS</div>
                      {contributions.filter(item => item.status === "active").map(item => (
                        <div className="draft-source-group" key={item.id}>
                          <label className="draft-source-option">
                            <input
                              type="checkbox"
                              checked={draftSourceIds.includes(item.current_revision_id)}
                              onChange={event => setDraftSourceIds(current => event.target.checked
                                ? [...current, item.current_revision_id]
                                : current.filter(id => id !== item.current_revision_id))}
                            />
                            <span><strong>{item.title}</strong><small>{item.author_display_name} · revision {item.current_revision_number}</small></span>
                          </label>
                          {acceptedDraftSuggestions.filter(suggestion => suggestion.target_revision_id === item.current_revision_id).map(suggestion => (
                            <label className="draft-suggestion-option" key={suggestion.id}>
                              <input
                                type="checkbox"
                                checked={selectedDraftSuggestionIds.includes(suggestion.id)}
                                onChange={event => setSelectedDraftSuggestionIds(current => event.target.checked
                                  ? [...current, suggestion.id]
                                  : current.filter(id => id !== suggestion.id))}
                              />
                              <span><strong>Include accepted suggestion: {suggestion.title}</strong><small>{suggestion.author_display_name}</small></span>
                            </label>
                          ))}
                        </div>
                      ))}
                      {contributions.every(item => item.status !== "active") && <p className="muted-note">Add an active contribution before compiling a draft.</p>}
                    </div>
                    <div className="form-actions">
                      <span>{draftSourceIds.length} source revision{draftSourceIds.length === 1 ? "" : "s"} selected. Withdrawn contributions are excluded.</span>
                      <button className="primary-button" type="submit" disabled={loading || draftSourceIds.length === 0}>
                        <Sparkles size={15} /> Assemble draft proposal
                      </button>
                    </div>
                  </form>
                )}
                {!canContribute && !draft && <p className="muted-note">A project contributor can compile the first narrative proposal.</p>}
                {selectedProject.current_phase === "storyboard" && <p className="muted-note">Narrative drafting is locked because this project has entered storyboarding.</p>}
                {draft && latestDraftVersion && (
                  <div className="draft-workspace">
                    <div className="draft-version-bar">
                      <div><div className="section-kicker">{selectedDraftVersion?.id === latestDraftVersion.id ? "CURRENT PROPOSAL" : "HISTORIC PROPOSAL"}</div><h3>{selectedDraftVersion?.title || latestDraftVersion.title}</h3>
                        <p>Version {selectedDraftVersion?.version_number || latestDraftVersion.version_number} · {selectedDraftVersion?.origin === "manual" ? "Manually revised" : "Compiled proposal"} · {selectedDraftVersion?.author_display_name}</p>
                      </div>
                      {canContribute && selectedProject.current_phase !== "storyboard" && !editingDraft && selectedDraftVersion?.id === latestDraftVersion.id && <button className="secondary-button" type="button" onClick={startDraftRevision}><RotateCcw size={14} /> Revise proposal</button>}
                    </div>
                    {editingDraft ? (
                      <form className="draft-editor" onSubmit={saveDraftRevision}>
                        <label>Proposal title<input required maxLength={160} value={draftEditTitle} onChange={event => setDraftEditTitle(event.target.value)} /></label>
                        <label>Revised narrative<textarea required rows={18} maxLength={100000} value={draftEditContent} onChange={event => setDraftEditContent(event.target.value)} /></label>
                        <div className="form-actions"><span>Saving creates a new immutable version and carries forward its source map.</span>
                          <button className="quiet-button" type="button" onClick={() => setEditingDraft(false)}>Cancel</button>
                          <button className="primary-button" type="submit" disabled={loading || !draftEditTitle.trim() || !draftEditContent.trim()}>Save new version</button>
                        </div>
                      </form>
                    ) : (
                      <pre className="draft-preview">{selectedDraftVersion?.content || latestDraftVersion.content}</pre>
                    )}
                    <div className="draft-provenance">
                      <div className="section-kicker">SOURCE PROVENANCE · {selectedDraftVersion?.sources.length || 0} REFERENCES</div>
                      {(selectedDraftVersion?.sources || []).map(source => (
                        <details className="draft-provenance-item" key={source.id}>
                          <summary className="draft-provenance-row">
                            <span>{source.source_order.toString().padStart(2, "0")}</span>
                            <strong>{source.source_title}</strong>
                            <small>{source.source_kind === "accepted_suggestion" ? "Accepted suggestion" : "Contribution revision"}</small>
                          </summary>
                          <pre>{source.source_text_snapshot}</pre>
                        </details>
                      ))}
                      <p className="muted-note">Each reference stores the exact source text snapshot as well as its contribution and revision identifiers.</p>
                    </div>

                    {selectedApproval && selectedDraftVersion && (
                      <section className="approval-panel">
                        <div className="approval-heading">
                          <div><div className="section-kicker">VERSION-SPECIFIC DECISION</div><h3>Review and approval</h3></div>
                          <div className="approval-heading-actions">
                            <span className={selectedApproval.decision_outcome === "approved" ? "approval-status approved" : selectedApproval.decision_outcome === "rejected" ? "approval-status rejected" : "approval-status pending"}>
                              {selectedApproval.decision_outcome || "Awaiting decision"}
                            </span>
                            <button type="button" className="quiet-button" onClick={() => loadApproval(selectedProject.id).catch(err => setError(err instanceof Error ? err.message : "Could not refresh votes."))}>Refresh tally</button>
                          </div>
                        </div>
                        <div className="approval-tally">
                          <div><strong>{selectedApproval.approve_count}</strong><span>Approve votes</span></div>
                          <div><strong>{selectedApproval.reject_count}</strong><span>Reject votes</span></div>
                          <div><strong>{selectedApproval.required_votes}</strong><span>Matching votes required</span></div>
                          <div><strong>{selectedApproval.eligible_voter_count}</strong><span>Eligible voters</span></div>
                        </div>
                        <p className="approval-ballot-note">
                          Rule: {selectedApproval.rule_mode === "majority" ? "majority" : "owner approval"}
                          {selectedApproval.ballot_opened_at ? ` · Ballot opened ${new Date(selectedApproval.ballot_opened_at).toLocaleString()} · electorate and threshold are frozen` : " · electorate and threshold are captured when the first vote is cast"}
                        </p>
                        {selectedApproval.decision_outcome === null && selectedApproval.can_vote && (
                          <div className="approval-vote-form">
                            <label>Optional note<textarea rows={2} maxLength={3000} value={approvalNote} onChange={event => setApprovalNote(event.target.value)} placeholder="Add context for your vote…" /></label>
                            <div className="approval-actions">
                              <button type="button" className="secondary-button" disabled={loading || selectedApproval.current_user_vote === "approve"} onClick={() => castApprovalVote("approve")}>Approve this version</button>
                              <button type="button" className="secondary-button danger-button" disabled={loading || selectedApproval.current_user_vote === "reject"} onClick={() => castApprovalVote("reject")}>Reject this version</button>
                              {selectedApproval.current_user_vote && <small>Your current vote: {selectedApproval.current_user_vote}. You may change it before a final decision.</small>}
                            </div>
                          </div>
                        )}
                        {selectedApproval.decision_outcome === null && !selectedApproval.can_vote && !selectedApproval.can_finalize && (
                          <p className="muted-note">{selectedApproval.is_current_version ? "You cannot vote under the current approval rule, or this project is not accepting votes." : "Only the current draft version can receive votes."}</p>
                        )}
                        {selectedApproval.can_finalize && (
                          <div className="approval-finalize">
                            <p>{selectedApproval.approve_count >= selectedApproval.required_votes ? "The approval threshold has been reached." : "The rejection threshold has been reached."} The project owner can now record the final decision.</p>
                            <button className="primary-button" type="button" disabled={loading} onClick={finalizeApprovalDecision}>
                              {selectedApproval.approve_count >= selectedApproval.required_votes ? "Approve narrative & enter storyboarding" : "Finalize rejection"}
                            </button>
                          </div>
                        )}
                        {selectedApproval.decision && (
                          <div className={selectedApproval.decision.outcome === "approved" ? "approval-decision approved" : "approval-decision rejected"}>
                            <strong>{selectedApproval.decision.outcome === "approved" ? "Narrative version approved" : "Narrative version rejected"}</strong>
                            <span>Finalized by {selectedApproval.decision.actor_display_name} · {new Date(selectedApproval.decision.created_at).toLocaleString()}</span>
                            <small>Rule: {selectedApproval.decision.rule_mode === "majority" ? "majority" : "owner approval"} · {selectedApproval.decision.approve_count} approve / {selectedApproval.decision.reject_count} reject · {selectedApproval.decision.required_votes} required</small>
                            {selectedApproval.decision.note && <p>{selectedApproval.decision.note}</p>}
                          </div>
                        )}
                        <div className="approval-vote-history">
                          <div className="section-kicker">VOTE HISTORY</div>
                          {selectedApproval.votes.length === 0 && <p className="muted-note">No votes have been recorded for this version.</p>}
                          {selectedApproval.votes.map(vote => (
                            <div className="approval-vote-row" key={vote.id}>
                              <strong>{vote.voter_display_name}</strong>
                              <span className={vote.choice === "approve" ? "vote-choice approve" : "vote-choice reject"}>{vote.choice}</span>
                              <small>{new Date(vote.created_at).toLocaleString()}{vote.is_latest ? " · latest" : " · superseded"}{vote.counts_toward_result ? " · counted" : " · not counted"}</small>
                              {vote.note && <p>{vote.note}</p>}
                            </div>
                          ))}
                        </div>
                      </section>
                    )}

                    <div className="draft-history">
                      <div className="section-kicker">PROPOSAL HISTORY</div>
                      <div className="draft-history-list">{[...draft.versions].reverse().map(version => (
                        <button type="button" key={version.id} className={selectedDraftVersion?.id === version.id ? "draft-history-item selected" : "draft-history-item"} onClick={() => { setSelectedDraftVersionId(version.id); setEditingDraft(false); }}>
                          <strong>Version {version.version_number}</strong><span>{version.origin === "manual" ? "Manual revision" : "Compiled"} · {version.author_display_name}</span><small>{new Date(version.created_at).toLocaleString()}</small>
                        </button>
                      ))}</div>
                    </div>
                    <p className="draft-disclaimer">Votes are attached to this exact immutable version. Approval is a separate recorded decision; only an approved version advances the project to storyboarding.</p>
                  </div>
                )}
              </section>

                {approval && approval.phase_history.length > 0 && (
                  <section className="phase-history-panel">
                    <div className="section-kicker">PROJECT PHASE HISTORY</div>
                    {approval.phase_history.map(item => (
                      <div className="phase-history-row" key={item.id}>
                        <strong>{item.from_phase} → {item.to_phase}</strong>
                        <span>{item.actor_display_name} · {new Date(item.created_at).toLocaleString()}</span>
                        <small>{item.reason}</small>
                      </div>
                    ))}
                  </section>
                )}

              <section className="contributions-section">
                <div className="section-heading contribution-heading">
                  <div><div className="section-kicker">THE STORY TAKES SHAPE</div><h2>Contributions <span className="contribution-count">{contributions.length}</span></h2></div>
                  <span className="step-count">Independent ideas, preserved by author</span>
                </div>

                {canContribute && (
                  <form className="contribution-form" onSubmit={submitContribution}>
                    <div className="form-title"><div><div className="section-kicker">{editingContribution ? "NEW REVISION" : "ADD YOUR VOICE"}</div><h2>{editingContribution ? "Revise your contribution." : "Share a story contribution."}</h2></div>
                      {editingContribution && <button type="button" className="quiet-button" onClick={() => { setEditingContribution(false); setContributionTitle(""); setContributionBody(""); }}><X size={14} /> Cancel revision</button>}
                    </div>
                    <label>Contribution title<input required maxLength={160} placeholder="A working title for your idea" value={contributionTitle} onChange={e => setContributionTitle(e.target.value)} /></label>
                    <label>Your contribution<textarea required rows={7} maxLength={30000} placeholder="Write a scene, a character idea, a plot development, a setting, or any piece of the story you want to contribute…" value={contributionBody} onChange={e => setContributionBody(e.target.value)} /></label>
                    <div className="form-actions"><span>{editingContribution ? "Saving creates a new revision; previous versions remain available." : "Your contribution is saved separately and attributed to you."}</span><button className="primary-button" disabled={loading || !contributionTitle.trim() || !contributionBody.trim()} type="submit">{loading ? <LoaderCircle className="spin" size={16} /> : <Send size={15} />} {editingContribution ? "Save new revision" : "Submit contribution"}</button></div>
                  </form>
                )}
                {!canContribute && <p className="muted-note">You have read-only access to this project's contributions.</p>}

                {contributions.length === 0 ? (
                  <div className="empty-state compact-empty"><div className="empty-icon"><FileText size={23} /></div><h2>No contributions yet.</h2><p>This is where each participant's independent story ideas will appear.</p></div>
                ) : (
                  <div className="contribution-list">{contributions.map(item => (
                    <button className={selectedContribution?.id === item.id ? "contribution-card selected" : "contribution-card"} key={item.id} onClick={() => openContribution(item)}>
                      <div className="contribution-card-top"><span className="contribution-author">{item.author_display_name}</span><span className={item.status === "withdrawn" ? "status-tag withdrawn" : "status-tag"}>{item.status}</span></div>
                      <h3>{item.title}</h3><p>{item.current_body.length > 210 ? item.current_body.slice(0, 210) + "…" : item.current_body}</p>
                      <div className="contribution-card-bottom"><span><Clock3 size={13} /> {new Date(item.created_at).toLocaleString()}</span><span><History size={13} /> Revision {item.current_revision_number}</span></div>
                    </button>
                  ))}</div>
                )}

                {selectedContribution && (
                  <div className="contribution-detail">
                    <div className="contribution-detail-heading"><div><div className="section-kicker">CONTRIBUTION HISTORY</div><h2>{selectedContribution.title}</h2><p>By {selectedContribution.author_display_name} · {selectedContribution.status}</p></div><button className="quiet-button" onClick={() => setSelectedContribution(null)}><X size={15} /> Close</button></div>
                    <div className="current-contribution-text">{selectedContribution.current_body}</div>
                    {canReviseSelected && selectedContribution.status === "active" && <div className="contribution-actions"><button className="secondary-button" onClick={startRevision}><RotateCcw size={14} /> Create a revision</button><button className="quiet-button danger-button" onClick={() => withdrawContribution(selectedContribution)}>Withdraw contribution</button></div>}
                    <div className="revision-list"><div className="section-kicker">REVISION HISTORY</div>{[...selectedContribution.revisions].reverse().map(revision => (
                      <article className="revision-item" key={revision.id}><div className="revision-meta"><strong>Revision {revision.revision_number} · {revision.title}</strong><span>{revision.author_display_name} · {new Date(revision.created_at).toLocaleString()}</span></div><p>{revision.body}</p></article>
                    ))}</div>

                    <div className="discussion-grid">
                      <section className="discussion-panel">
                        <div className="section-kicker">PROJECT DISCUSSION</div><h3>Comments <span>{comments.length}</span></h3>
                        <div className="comment-list">{comments.map(comment => <article className="comment-item" key={comment.id}><div className="comment-meta"><strong>{comment.author_display_name}</strong><span>{new Date(comment.created_at).toLocaleString()}</span></div><p>{comment.body}</p></article>)}{comments.length === 0 && <p className="muted-note">No comments yet. Start the discussion.</p>}</div>
                        {canContribute && selectedContribution.status === "active" && <form className="discussion-form" onSubmit={submitComment}><textarea rows={3} required maxLength={10000} placeholder="Add a comment…" value={commentBody} onChange={e => setCommentBody(e.target.value)} /><button className="primary-button" type="submit" disabled={!commentBody.trim()}><Send size={14} /> Comment</button></form>}
                      </section>
                      <section className="discussion-panel">
                        <div className="section-kicker">PROPOSE AN ALTERNATIVE</div><h3>Suggestions <span>{suggestions.length}</span></h3>
                        <div className="suggestion-list">{suggestions.map(suggestion => <article className="suggestion-item" key={suggestion.id}><div className="suggestion-meta"><strong>{suggestion.title}</strong><span className="status-tag">{suggestion.status}</span></div><small>By {suggestion.author_display_name} · {new Date(suggestion.created_at).toLocaleDateString()}</small>{suggestion.rationale && <p>{suggestion.rationale}</p>}<div className="suggested-text">{suggestion.proposed_text}</div>{suggestion.decisions.map(decision => <small className="decision-line" key={decision.id}>{decision.actor_display_name}: {decision.new_status}{decision.note ? " — " + decision.note : ""}</small>)}{(myMembership?.role === "owner" || myMembership?.role === "editor") && !["accepted", "rejected"].includes(suggestion.status) && <div className="decision-actions"><button type="button" onClick={() => decideSuggestion(suggestion, "accepted")}>Accept</button><button type="button" onClick={() => decideSuggestion(suggestion, "deferred")}>Defer</button><button type="button" onClick={() => decideSuggestion(suggestion, "rejected")}>Reject</button></div>}</article>)}{suggestions.length === 0 && <p className="muted-note">No suggestions yet.</p>}</div>
                        {canContribute && selectedContribution.status === "active" && <form className="discussion-form" onSubmit={submitSuggestion}><input required maxLength={160} placeholder="Suggestion title" value={suggestionTitle} onChange={e => setSuggestionTitle(e.target.value)} /><textarea rows={2} maxLength={10000} placeholder="Why would this improve the contribution? (optional)" value={suggestionRationale} onChange={e => setSuggestionRationale(e.target.value)} /><textarea rows={4} required maxLength={30000} placeholder="Your proposed alternative…" value={suggestionText} onChange={e => setSuggestionText(e.target.value)} /><button className="primary-button" type="submit" disabled={!suggestionTitle.trim() || !suggestionText.trim()}><Lightbulb size={14} /> Submit suggestion</button></form>}
                      </section>
                    </div>
                  </div>
                )}
              </section>
            </section>
          )}
          <footer className="footer"><span>STORYFORGE COLLECTIVE</span><span>Built together, one story at a time.</span></footer>
        </div>
      </section>
    </main>
  );
}

export default App;
