import { FormEvent, useEffect, useState } from "react";
import {
  ArrowLeft, ArrowUpRight, BookOpen, CheckCircle2, Clapperboard, Compass,
  Film, Lightbulb, Plus, Sparkles, Users, FolderOpen, LoaderCircle,
  FileText, History, Send, Clock3, RotateCcw, X,
} from "lucide-react";

type ApiHealth = { status: string; service: string; version: string };
type CurrentUser = { id: string; display_name: string; email: string };
type ProjectFormat = "movie" | "tv_series";
type ProjectCategory = "fiction" | "documentary";
type Project = {
  id: string; title: string; description: string; logline: string; genre: string;
  format: ProjectFormat; category: ProjectCategory;
  visibility: string; current_phase: string; owner_user_id: string;
  created_at: string; updated_at: string; member_count: number;
};
type Member = {
  id: string; display_name: string | null; email: string | null;
  invited_email: string | null; role: string; status: string; created_at: string;
};
type ProjectDetail = Project & { members: Member[] };
type ProjectForm = { title: string; logline: string; genre: string; description: string; format: ProjectFormat; category: ProjectCategory; visibility: string };
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
type CharacterEditDraft = {
  name: string; description: string; visual_description: string; personality_notes: string;
};
type LocationEditDraft = {
  name: string; description: string; environment_type: string; time_period: string; visual_notes: string;
};
type StoryboardEpisode = {
  id: string; season_id: string; episode_number: number; title: string;
  logline: string; synopsis: string; estimated_duration_seconds: number | null;
  status: string; created_by_user_id: string; created_at: string; updated_at: string;
};
type StoryboardSeason = {
  id: string; storyboard_id: string; season_number: number; title: string;
  description: string; story_arc: string; status: string;
  created_by_user_id: string; created_at: string; updated_at: string;
  episodes: StoryboardEpisode[];
};
type ScenePassage = {
  id: string; reference_order: number; start_offset: number; end_offset: number;
  passage_snapshot: string; created_by_user_id: string; created_at: string;
};
type ScriptElementType = "action" | "dialogue" | "parenthetical" | "transition" | "production_note";
type SceneScriptElement = {
  id: string; element_order: number; element_type: ScriptElementType; content: string;
  character_id: string | null; character_name: string | null; created_at: string;
};
type SceneScriptElementDraft = {
  element_type: ScriptElementType; content: string; character_id: string;
};
type SceneScriptVersion = {
  id: string; revision_number: number; content: string; parent_version_id: string | null;
  author_user_id: string; author_display_name: string; created_at: string;
  elements: SceneScriptElement[];
};
type SceneCharacter = { id: string; name: string; role_label: string; notes: string };
type StoryboardScene = {
  id: string; scene_order: number; title: string; summary: string; requirements: string;
  estimated_duration_seconds: number | null; location_id: string | null; location_name: string | null;
  episode_id: string | null; episode_title: string | null; season_number: number | null; episode_number: number | null;
  characters: SceneCharacter[]; passages: ScenePassage[]; script_versions: SceneScriptVersion[];
  created_by_user_id: string; created_at: string; updated_at: string;
};
type Storyboard = {
  id: string; project_id: string; title: string; narrative_version_id: string;
  narrative_version_number: number; narrative_title: string; narrative_content: string;
  created_by_user_id: string; created_at: string;
  scenes: StoryboardScene[]; seasons: StoryboardSeason[]; characters: ProjectCharacter[]; locations: ProjectLocation[];
};
type SceneEditDraft = {
  title: string; summary: string; requirements: string;
  estimated_duration_seconds: string; location_id: string; episode_id: string; character_ids: string[];
};

type DocumentarySourceType = "article" | "book" | "academic_paper" | "official_record" | "government_data" | "interview" | "archival_record" | "website" | "other";
type DocumentaryEvidenceRelation = "supports" | "challenges" | "context";
type DocumentaryReviewResult = "supported" | "contested" | "not_supported" | "insufficient_evidence";
type DocumentaryResearchSource = {
  id: string; project_id: string; title: string; source_type: DocumentarySourceType;
  creator: string; publisher: string; publication_date: string; url: string | null;
  citation_text: string; research_notes: string; status: string;
  created_by_user_id: string; created_at: string; updated_at: string; accessed_at: string;
};
type DocumentaryClaimEvidence = {
  id: string; source_id: string; source_title: string; source_type: DocumentarySourceType;
  source_url: string | null; source_status: string; evidence_relation: DocumentaryEvidenceRelation;
  excerpt: string; locator: string; notes: string; created_by_user_id: string; created_at: string;
};
type DocumentaryClaimReview = {
  id: string; previous_status: string; result: DocumentaryReviewResult; rationale: string;
  reviewed_evidence_snapshot: Array<Record<string, string | null>>;
  reviewer_user_id: string; reviewer_display_name: string; created_at: string;
};
type DocumentaryClaim = {
  id: string; project_id: string; statement: string; context: string;
  origin: "human" | "ai_assisted"; status: string; current_review_status: string;
  created_by_user_id: string; created_by_display_name: string;
  created_at: string; updated_at: string;
  evidence: DocumentaryClaimEvidence[]; reviews: DocumentaryClaimReview[];
};
type DocumentaryResearch = {
  project_id: string; sources: DocumentaryResearchSource[]; claims: DocumentaryClaim[];
};

type DocumentaryConsentUse = "research" | "storyboard" | "script" | "narration" | "lower_third" | "caption" | "promotion" | "publication" | "trailer" | "social";
type DocumentaryIdentityMode = "named" | "pseudonym" | "anonymous";
type DocumentaryInterviewSubject = {
  id: string; project_id: string; name_or_pseudonym: string; identity_mode: DocumentaryIdentityMode;
  role_or_relationship: string; background_notes: string; status: string;
  created_by_user_id: string; created_at: string; updated_at: string;
};
type DocumentaryInterviewSession = {
  id: string; project_id: string; subject_id: string; subject_label: string; session_date: string;
  interviewer_name: string; session_format: string; location_or_platform: string; transcript_notes: string;
  status: string; media_asset_ids: string[]; created_by_user_id: string; created_at: string; updated_at: string;
};
type DocumentaryReleaseEvent = {
  id: string; actor_user_id: string; previous_status: string | null; new_status: string; reason: string; created_at: string;
};
type DocumentaryRelease = {
  id: string; project_id: string; subject_id: string; subject_label: string; interview_session_id: string | null;
  scope_type: "project" | "production" | "release"; scope_label: string; consent_scope: string; withdrawal_terms: string;
  permitted_uses: DocumentaryConsentUse[]; status: "draft" | "signed" | "withdrawn" | "expired";
  signed_at: string | null; expires_at: string | null; release_document_asset_id: string | null;
  created_by_user_id: string; created_at: string; updated_at: string; events: DocumentaryReleaseEvent[];
};
type DocumentaryMediaRights = {
  id: string; media_asset_id: string; version_number: number; supersedes_rights_id: string | null;
  rights_holder: string; rights_basis: string; license_name: string; license_url: string; territory: string;
  valid_from: string | null; valid_until: string | null; permitted_uses: DocumentaryConsentUse[];
  attribution_required: boolean; attribution_text: string; restrictions: string; status: string;
  created_by_user_id: string; created_at: string;
};
type DocumentaryMediaAsset = {
  id: string; project_id: string; source_id: string | null; interview_session_id: string | null;
  title: string; asset_type: string; original_filename: string; content_type: string; size_bytes: number;
  sha256: string; duration_seconds: number | null; status: string; download_url: string;
  latest_rights: DocumentaryMediaRights | null; created_by_user_id: string; created_at: string; updated_at: string;
};
type DocumentaryClaimUsage = {
  id: string; claim_id: string; claim_statement: string; claim_review_status: string; usage_type: string;
  scene_id: string | null; scene_title: string | null; script_version_id: string | null;
  script_revision_number: number | null; reference_text: string; created_by_user_id: string; created_at: string;
};
type DocumentaryProduction = {
  project_id: string; subjects: DocumentaryInterviewSubject[]; sessions: DocumentaryInterviewSession[];
  releases: DocumentaryRelease[]; media_assets: DocumentaryMediaAsset[]; claim_usages: DocumentaryClaimUsage[];
};
type DocumentaryMediaRightsDraft = {
  rights_holder: string; rights_basis: string; license_name: string; license_url: string; territory: string;
  valid_until: string; permitted_uses: DocumentaryConsentUse[]; attribution_required: boolean; attribution_text: string; restrictions: string;
};
type DocumentaryClaimUsageDraft = { usage_type: string; scene_id: string; script_version_id: string; reference_text: string };
const documentaryUseOptions: { value: DocumentaryConsentUse; label: string }[] = [
  { value: "research", label: "Research" }, { value: "storyboard", label: "Storyboard" },
  { value: "script", label: "Script" }, { value: "narration", label: "Narration" },
  { value: "lower_third", label: "Lower thirds" }, { value: "caption", label: "Captions" },
  { value: "promotion", label: "Promotion" }, { value: "publication", label: "Publication" },
  { value: "trailer", label: "Trailer" }, { value: "social", label: "Social media" },
];


const phases = [
  { number: "01", title: "Story contributions", detail: "Bring your first ideas to the table.", icon: BookOpen, state: "active" },
  { number: "02", title: "Develop the story", detail: "Discuss, combine and shape the narrative.", icon: Lightbulb, state: "upcoming" },
  { number: "03", title: "Storyboard", detail: "Turn the story into scenes.", icon: Clapperboard, state: "upcoming" },
  { number: "04", title: "Bring it to life", detail: "Cast, perform, direct and edit.", icon: Film, state: "upcoming" },
];

const emptyForm: ProjectForm = { title: "", logline: "", genre: "", description: "", format: "movie", category: "fiction", visibility: "private" };

async function apiUpload<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(path, { method: "POST", body });
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new Error(result?.detail || `Upload failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

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
  const [documentaryResearch, setDocumentaryResearch] = useState<DocumentaryResearch | null>(null);
  const [documentaryProduction, setDocumentaryProduction] = useState<DocumentaryProduction | null>(null);
  const [interviewSubjectLabel, setInterviewSubjectLabel] = useState("");
  const [interviewSubjectMode, setInterviewSubjectMode] = useState<DocumentaryIdentityMode>("named");
  const [interviewSubjectRole, setInterviewSubjectRole] = useState("");
  const [interviewSubjectNotes, setInterviewSubjectNotes] = useState("");
  const [interviewSessionSubjectId, setInterviewSessionSubjectId] = useState("");
  const [interviewSessionDate, setInterviewSessionDate] = useState("");
  const [interviewSessionInterviewer, setInterviewSessionInterviewer] = useState("");
  const [interviewSessionFormat, setInterviewSessionFormat] = useState("in_person");
  const [interviewSessionLocation, setInterviewSessionLocation] = useState("");
  const [interviewSessionNotes, setInterviewSessionNotes] = useState("");
  const [releaseSubjectId, setReleaseSubjectId] = useState("");
  const [releaseSessionId, setReleaseSessionId] = useState("");
  const [releaseScopeType, setReleaseScopeType] = useState<"project" | "production" | "release">("project");
  const [releaseScopeLabel, setReleaseScopeLabel] = useState("");
  const [releaseConsentScope, setReleaseConsentScope] = useState("");
  const [releaseWithdrawalTerms, setReleaseWithdrawalTerms] = useState("");
  const [releaseStatus, setReleaseStatus] = useState<"draft" | "signed">("draft");
  const [releaseSignedAt, setReleaseSignedAt] = useState("");
  const [releaseExpiresAt, setReleaseExpiresAt] = useState("");
  const [releaseDocumentAssetId, setReleaseDocumentAssetId] = useState("");
  const [releasePermittedUses, setReleasePermittedUses] = useState<DocumentaryConsentUse[]>(["research", "storyboard"]);
  const [documentaryUploadTitle, setDocumentaryUploadTitle] = useState("");
  const [documentaryUploadType, setDocumentaryUploadType] = useState("document");
  const [documentaryUploadSourceId, setDocumentaryUploadSourceId] = useState("");
  const [documentaryUploadSessionId, setDocumentaryUploadSessionId] = useState("");
  const [documentaryUploadDuration, setDocumentaryUploadDuration] = useState("");
  const [documentaryUploadFile, setDocumentaryUploadFile] = useState<File | null>(null);
  const [mediaRightsDrafts, setMediaRightsDrafts] = useState<Record<string, DocumentaryMediaRightsDraft>>({});
  const [claimUsageDrafts, setClaimUsageDrafts] = useState<Record<string, DocumentaryClaimUsageDraft>>({});
  const [researchSourceTitle, setResearchSourceTitle] = useState("");
  const [researchSourceType, setResearchSourceType] = useState<DocumentarySourceType>("article");
  const [researchSourceCreator, setResearchSourceCreator] = useState("");
  const [researchSourcePublisher, setResearchSourcePublisher] = useState("");
  const [researchSourceDate, setResearchSourceDate] = useState("");
  const [researchSourceAccessedAt, setResearchSourceAccessedAt] = useState("");
  const [researchSourceUrl, setResearchSourceUrl] = useState("");
  const [researchSourceCitation, setResearchSourceCitation] = useState("");
  const [researchSourceNotes, setResearchSourceNotes] = useState("");
  const [claimStatement, setClaimStatement] = useState("");
  const [claimContext, setClaimContext] = useState("");
  const [claimOrigin, setClaimOrigin] = useState<"human" | "ai_assisted">("human");
  const [evidenceSourceIds, setEvidenceSourceIds] = useState<Record<string, string>>({});
  const [evidenceRelations, setEvidenceRelations] = useState<Record<string, DocumentaryEvidenceRelation>>({});
  const [evidenceExcerpts, setEvidenceExcerpts] = useState<Record<string, string>>({});
  const [evidenceLocators, setEvidenceLocators] = useState<Record<string, string>>({});
  const [evidenceNotesByClaim, setEvidenceNotesByClaim] = useState<Record<string, string>>({});
  const [reviewResults, setReviewResults] = useState<Record<string, DocumentaryReviewResult>>({});
  const [reviewRationales, setReviewRationales] = useState<Record<string, string>>({});
  const [characterName, setCharacterName] = useState("");
  const [characterDescription, setCharacterDescription] = useState("");
  const [characterVisual, setCharacterVisual] = useState("");
  const [characterPersonality, setCharacterPersonality] = useState("");
  const [characterEdits, setCharacterEdits] = useState<Record<string, CharacterEditDraft>>({});
  const [showArchivedCharacters, setShowArchivedCharacters] = useState(false);
  const [locationEdits, setLocationEdits] = useState<Record<string, LocationEditDraft>>({});
  const [showArchivedLocations, setShowArchivedLocations] = useState(false);
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
  const [sceneEpisodeId, setSceneEpisodeId] = useState("");
  const [seasonNumber, setSeasonNumber] = useState("1");
  const [seasonTitle, setSeasonTitle] = useState("");
  const [seasonDescription, setSeasonDescription] = useState("");
  const [seasonStoryArc, setSeasonStoryArc] = useState("");
  const [episodeSeasonId, setEpisodeSeasonId] = useState("");
  const [episodeNumber, setEpisodeNumber] = useState("1");
  const [episodeTitle, setEpisodeTitle] = useState("");
  const [episodeLogline, setEpisodeLogline] = useState("");
  const [episodeSynopsis, setEpisodeSynopsis] = useState("");
  const [episodeDuration, setEpisodeDuration] = useState("");
  const [sceneCharacterIds, setSceneCharacterIds] = useState<string[]>([]);
  const [sceneEdits, setSceneEdits] = useState<Record<string, SceneEditDraft>>({});
  const [scriptElementDrafts, setScriptElementDrafts] = useState<Record<string, SceneScriptElementDraft[]>>({});
  const [scriptEditorOpen, setScriptEditorOpen] = useState<Record<string, boolean>>({});
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
      const [detail, items, currentDraft, approvalOverview, currentStoryboard] = await Promise.all([
        api<ProjectDetail>(`/api/projects/${projectId}`),
        api<Contribution[]>(`/api/projects/${projectId}/contributions`),
        api<NarrativeDraft | null>(`/api/projects/${projectId}/draft`),
        api<ApprovalOverview>(`/api/projects/${projectId}/approval`),
        api<Storyboard | null>(`/api/projects/${projectId}/storyboard`),
      ]);
      const currentResearch = detail.category === "documentary"
        ? await api<DocumentaryResearch>(`/api/projects/${projectId}/documentary`)
        : null;
      const currentProduction = detail.category === "documentary"
        ? await api<DocumentaryProduction>(`/api/projects/${projectId}/documentary/production`)
        : null;
      setSelectedProject(detail);
      setDocumentaryResearch(currentResearch);
      setDocumentaryProduction(currentProduction);
      setResearchSourceTitle(""); setResearchSourceType("article");
      setResearchSourceCreator(""); setResearchSourcePublisher(""); setResearchSourceDate(""); setResearchSourceAccessedAt("");
      setResearchSourceUrl(""); setResearchSourceCitation(""); setResearchSourceNotes("");
      setClaimStatement(""); setClaimContext(""); setClaimOrigin("human");
      setEvidenceSourceIds({}); setEvidenceRelations({}); setEvidenceExcerpts({}); setEvidenceLocators({}); setEvidenceNotesByClaim({});
      setReviewResults({}); setReviewRationales({});
      setInterviewSubjectLabel(""); setInterviewSubjectMode("named"); setInterviewSubjectRole(""); setInterviewSubjectNotes("");
      setInterviewSessionSubjectId(""); setInterviewSessionDate(""); setInterviewSessionInterviewer(""); setInterviewSessionFormat("in_person"); setInterviewSessionLocation(""); setInterviewSessionNotes("");
      setReleaseSubjectId(""); setReleaseSessionId(""); setReleaseScopeType("project"); setReleaseScopeLabel(""); setReleaseConsentScope(""); setReleaseWithdrawalTerms("");
      setReleaseStatus("draft"); setReleaseSignedAt(""); setReleaseExpiresAt(""); setReleaseDocumentAssetId(""); setReleasePermittedUses(["research", "storyboard"]);
      setDocumentaryUploadTitle(""); setDocumentaryUploadType("document"); setDocumentaryUploadSourceId(""); setDocumentaryUploadSessionId(""); setDocumentaryUploadDuration(""); setDocumentaryUploadFile(null);
      setMediaRightsDrafts({}); setClaimUsageDrafts({});
      setStoryboard(currentStoryboard);
      setCharacterEdits({}); setShowArchivedCharacters(false);
      setLocationEdits({}); setShowArchivedLocations(false);
      setSceneEdits({});
      setScriptElementDrafts({});
      setScriptEditorOpen({});
      setPassageDrafts({});
      setPassageOccurrences({});
      setSceneTitle(""); setSceneSummary(""); setSceneRequirements("");
      setSceneDuration(""); setSceneLocationId(""); setSceneEpisodeId(""); setSceneCharacterIds([]);
      setSeasonNumber("1"); setSeasonTitle(""); setSeasonDescription(""); setSeasonStoryArc("");
      setEpisodeSeasonId(""); setEpisodeNumber("1"); setEpisodeTitle(""); setEpisodeLogline(""); setEpisodeSynopsis(""); setEpisodeDuration("");
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

  async function initializeStoryboard() {
    if (!selectedProject) return;
    setLoading(true);
    setError("");
    try {
      const created = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard`, { method: "POST" });
      setStoryboard(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not initialize the storyboard.");
    } finally {
      setLoading(false);
    }
  }

  async function submitCharacter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !characterName.trim()) return;
    setLoading(true);
    setError("");
    try {
      const created = await api<ProjectCharacter>(`/api/projects/${selectedProject.id}/storyboard/characters`, {
        method: "POST",
        body: JSON.stringify({
          name: characterName, description: characterDescription,
          visual_description: characterVisual, personality_notes: characterPersonality,
        }),
      });
      setStoryboard(current => current ? { ...current, characters: [...current.characters, created].sort((a, b) => a.name.localeCompare(b.name)) } : current);
      setCharacterName(""); setCharacterDescription(""); setCharacterVisual(""); setCharacterPersonality("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create character.");
    } finally {
      setLoading(false);
    }
  }

  async function submitLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !locationName.trim()) return;
    setLoading(true);
    setError("");
    try {
      const created = await api<ProjectLocation>(`/api/projects/${selectedProject.id}/storyboard/locations`, {
        method: "POST",
        body: JSON.stringify({
          name: locationName, description: locationDescription, environment_type: locationType,
          time_period: locationPeriod, visual_notes: locationVisual,
        }),
      });
      setStoryboard(current => current ? { ...current, locations: [...current.locations, created].sort((a, b) => a.name.localeCompare(b.name)) } : current);
      setLocationName(""); setLocationDescription(""); setLocationPeriod(""); setLocationVisual("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create location.");
    } finally {
      setLoading(false);
    }
  }

  function characterEditDraft(character: ProjectCharacter): CharacterEditDraft {
    return characterEdits[character.id] || {
      name: character.name,
      description: character.description,
      visual_description: character.visual_description,
      personality_notes: character.personality_notes,
    };
  }

  function locationEditDraft(location: ProjectLocation): LocationEditDraft {
    return locationEdits[location.id] || {
      name: location.name,
      description: location.description,
      environment_type: location.environment_type,
      time_period: location.time_period,
      visual_notes: location.visual_notes,
    };
  }

  async function saveCharacterDetails(character: ProjectCharacter) {
    if (!selectedProject) return;
    const edit = characterEditDraft(character);
    if (!edit.name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<ProjectCharacter>(`/api/projects/${selectedProject.id}/storyboard/characters/${character.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: edit.name,
          description: edit.description,
          visual_description: edit.visual_description,
          personality_notes: edit.personality_notes,
        }),
      });
      setStoryboard(current => current ? {
        ...current,
        characters: current.characters.map(item => item.id === updated.id ? updated : item).sort((a, b) => a.name.localeCompare(b.name)),
        scenes: current.scenes.map(scene => ({
          ...scene,
          characters: scene.characters.map(item => item.id === updated.id ? { ...item, name: updated.name } : item),
        })),
      } : current);
      setCharacterEdits(current => {
        const next = { ...current };
        delete next[character.id];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update character profile.");
    } finally {
      setLoading(false);
    }
  }

  async function updateCharacterStatus(character: ProjectCharacter, status: "active" | "archived") {
    if (!selectedProject) return;
    const explanation = status === "archived"
      ? "Archive this character? Existing scene participation and screenplay history will remain. The character cannot be newly assigned or selected for new dialogue."
      : "Restore this character? It will become available for new scene assignments and dialogue again.";
    if (!window.confirm(explanation)) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<ProjectCharacter>(`/api/projects/${selectedProject.id}/storyboard/characters/${character.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setStoryboard(current => current ? {
        ...current,
        characters: current.characters.map(item => item.id === updated.id ? updated : item),
      } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update character status.");
    } finally {
      setLoading(false);
    }
  }

  async function saveLocationDetails(location: ProjectLocation) {
    if (!selectedProject) return;
    const edit = locationEditDraft(location);
    if (!edit.name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<ProjectLocation>(`/api/projects/${selectedProject.id}/storyboard/locations/${location.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: edit.name,
          description: edit.description,
          environment_type: edit.environment_type,
          time_period: edit.time_period,
          visual_notes: edit.visual_notes,
        }),
      });
      setStoryboard(current => current ? {
        ...current,
        locations: current.locations.map(item => item.id === updated.id ? updated : item).sort((a, b) => a.name.localeCompare(b.name)),
        scenes: current.scenes.map(scene => scene.location_id === updated.id ? { ...scene, location_name: updated.name } : scene),
      } : current);
      setLocationEdits(current => {
        const next = { ...current };
        delete next[location.id];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update location profile.");
    } finally {
      setLoading(false);
    }
  }

  async function updateLocationStatus(location: ProjectLocation, status: "active" | "archived") {
    if (!selectedProject) return;
    const explanation = status === "archived"
      ? "Archive this location? Existing scenes will keep their location reference, but new scenes cannot use it."
      : "Restore this location so it can be selected for new scenes again?";
    if (!window.confirm(explanation)) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<ProjectLocation>(`/api/projects/${selectedProject.id}/storyboard/locations/${location.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setStoryboard(current => current ? {
        ...current,
        locations: current.locations.map(item => item.id === updated.id ? updated : item),
      } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update location status.");
    } finally {
      setLoading(false);
    }
  }

  async function submitSeason(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !storyboard || !seasonTitle.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/seasons`, {
        method: "POST",
        body: JSON.stringify({
          season_number: Number(seasonNumber), title: seasonTitle,
          description: seasonDescription, story_arc: seasonStoryArc,
        }),
      });
      setStoryboard(updated);
      const createdSeason = updated.seasons.find(item => item.season_number === Number(seasonNumber));
      if (createdSeason) setEpisodeSeasonId(createdSeason.id);
      setSeasonNumber(String(Math.max(0, ...updated.seasons.map(item => item.season_number)) + 1));
      setSeasonTitle(""); setSeasonDescription(""); setSeasonStoryArc("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create season.");
    } finally {
      setLoading(false);
    }
  }

  async function submitEpisode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !storyboard || !episodeSeasonId || !episodeTitle.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/seasons/${episodeSeasonId}/episodes`, {
        method: "POST",
        body: JSON.stringify({
          episode_number: Number(episodeNumber), title: episodeTitle,
          logline: episodeLogline, synopsis: episodeSynopsis,
          estimated_duration_seconds: episodeDuration.trim() ? Number(episodeDuration) : null,
        }),
      });
      setStoryboard(updated);
      const selectedSeason = updated.seasons.find(item => item.id === episodeSeasonId);
      setEpisodeNumber(String(Math.max(0, ...(selectedSeason?.episodes || []).map(item => item.episode_number)) + 1));
      setEpisodeTitle(""); setEpisodeLogline(""); setEpisodeSynopsis(""); setEpisodeDuration("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create episode.");
    } finally {
      setLoading(false);
    }
  }

  async function updateSeasonStatus(season: StoryboardSeason, status: "active" | "archived") {
    if (!selectedProject || !window.confirm(`${status === "archived" ? "Archive" : "Restore"} Season ${season.season_number}? Existing episodes, scenes and scripts will be preserved.`)) return;
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/seasons/${season.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setStoryboard(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update season.");
    }
  }

  async function updateEpisodeStatus(episode: StoryboardEpisode, status: "active" | "archived") {
    if (!selectedProject || !window.confirm(`${status === "archived" ? "Archive" : "Restore"} this episode? Its scenes and scripts will be preserved.`)) return;
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/episodes/${episode.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setStoryboard(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update episode.");
    }
  }

  async function submitScene(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !sceneTitle.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/scenes`, {
        method: "POST",
        body: JSON.stringify({
          title: sceneTitle, summary: sceneSummary, requirements: sceneRequirements,
          estimated_duration_seconds: sceneDuration.trim() ? Number(sceneDuration) : null,
          location_id: sceneLocationId || null,
          episode_id: selectedProject.format === "tv_series" ? (sceneEpisodeId || null) : null,
          character_ids: sceneCharacterIds,
        }),
      });
      setStoryboard(updated);
      setSceneTitle(""); setSceneSummary(""); setSceneRequirements("");
      setSceneDuration(""); setSceneLocationId(""); setSceneEpisodeId(""); setSceneCharacterIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create scene.");
    } finally {
      setLoading(false);
    }
  }

  function sceneEditDraft(scene: StoryboardScene): SceneEditDraft {
    return sceneEdits[scene.id] || {
      title: scene.title,
      summary: scene.summary,
      requirements: scene.requirements,
      estimated_duration_seconds: scene.estimated_duration_seconds?.toString() || "",
      location_id: scene.location_id || "",
      episode_id: scene.episode_id || "",
      character_ids: scene.characters.map(character => character.id),
    };
  }

  async function saveSceneDetails(scene: StoryboardScene) {
    if (!selectedProject) return;
    const edit = sceneEditDraft(scene);
    if (!edit.title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/scenes/${scene.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: edit.title, summary: edit.summary, requirements: edit.requirements,
          estimated_duration_seconds: edit.estimated_duration_seconds.trim() ? Number(edit.estimated_duration_seconds) : null,
          location_id: edit.location_id || null,
          episode_id: selectedProject.format === "tv_series" ? (edit.episode_id || null) : null,
          character_ids: edit.character_ids,
        }),
      });
      setStoryboard(updated);
      setSceneEdits(current => {
        const next = { ...current };
        delete next[scene.id];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update scene details.");
    } finally {
      setLoading(false);
    }
  }

  function startStructuredScriptEdit(scene: StoryboardScene) {
    const latest = scene.script_versions[scene.script_versions.length - 1] || null;
    setScriptElementDrafts(current => ({
      ...current,
      [scene.id]: current[scene.id] || (latest?.elements.length
        ? latest.elements.map(element => ({
            element_type: element.element_type,
            content: element.content,
            character_id: element.character_id || "",
          }))
        : [{ element_type: "action", content: latest?.content || "", character_id: "" }]),
    }));
    setScriptEditorOpen(current => ({ ...current, [scene.id]: true }));
  }

  function addScriptElement(sceneId: string, elementType: ScriptElementType) {
    setScriptElementDrafts(current => ({
      ...current,
      [sceneId]: [
        ...(current[sceneId] || []),
        { element_type: elementType, content: "", character_id: "" },
      ],
    }));
    setScriptEditorOpen(current => ({ ...current, [sceneId]: true }));
  }

  function updateScriptElement(sceneId: string, index: number, changes: Partial<SceneScriptElementDraft>) {
    setScriptElementDrafts(current => ({
      ...current,
      [sceneId]: (current[sceneId] || []).map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...changes } : item
      ),
    }));
  }

  function removeScriptElement(sceneId: string, index: number) {
    setScriptElementDrafts(current => ({
      ...current,
      [sceneId]: (current[sceneId] || []).filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  function cancelStructuredScriptEdit(sceneId: string) {
    setScriptElementDrafts(current => {
      const next = { ...current };
      delete next[sceneId];
      return next;
    });
    setScriptEditorOpen(current => ({ ...current, [sceneId]: false }));
  }

  function moveScriptElement(sceneId: string, index: number, direction: -1 | 1) {
    setScriptElementDrafts(current => {
      const elements = [...(current[sceneId] || [])];
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= elements.length) return current;
      [elements[index], elements[targetIndex]] = [elements[targetIndex], elements[index]];
      return { ...current, [sceneId]: elements };
    });
  }

  async function saveSceneScript(scene: StoryboardScene) {
    if (!selectedProject) return;
    const latest = scene.script_versions[scene.script_versions.length - 1] || null;
    const elements = scriptElementDrafts[scene.id] || [];
    if (elements.length === 0 || elements.some(item => !item.content.trim())) {
      setError("Add at least one non-empty screenplay block before saving.");
      return;
    }
    if (elements.some(item => item.element_type === "dialogue" && !item.character_id)) {
      setError("Every dialogue block needs a speaking character.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/scenes/${scene.id}/script`, {
        method: "POST",
        body: JSON.stringify({
          base_version_id: latest?.id || null,
          elements: elements.map(item => ({
            element_type: item.element_type,
            content: item.content,
            character_id: item.character_id || null,
          })),
        }),
      });
      setStoryboard(updated);
      setScriptElementDrafts(current => {
        const next = { ...current };
        delete next[scene.id];
        return next;
      });
      setScriptEditorOpen(current => ({ ...current, [scene.id]: false }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save script revision.");
    } finally {
      setLoading(false);
    }
  }

  async function addScenePassage(scene: StoryboardScene) {
    if (!selectedProject) return;
    const passageText = passageDrafts[scene.id] || "";
    if (!passageText.trim()) return;
    const occurrence = Number(passageOccurrences[scene.id] || "1");
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/scenes/${scene.id}/passages`, {
        method: "POST",
        body: JSON.stringify({ passage_text: passageText, occurrence }),
      });
      setStoryboard(updated);
      setPassageDrafts(current => ({ ...current, [scene.id]: "" }));
      setPassageOccurrences(current => ({ ...current, [scene.id]: "1" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not link the passage.");
    } finally {
      setLoading(false);
    }
  }

  async function moveScene(scene: StoryboardScene, direction: -1 | 1) {
    if (!selectedProject || !storyboard) return;
    const ordered = [...storyboard.scenes]
      .filter(item => item.episode_id === scene.episode_id)
      .sort((a, b) => a.scene_order - b.scene_order);
    const index = ordered.findIndex(item => item.id === scene.id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= ordered.length) return;
    [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
    setLoading(true);
    setError("");
    try {
      const updated = await api<Storyboard>(`/api/projects/${selectedProject.id}/storyboard/scenes/reorder`, {
        method: "PUT", body: JSON.stringify({ episode_id: scene.episode_id, scene_ids: ordered.map(item => item.id) }),
      });
      setStoryboard(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reorder scenes.");
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

  async function createResearchSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !researchSourceTitle.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<DocumentaryResearch>(`/api/projects/${selectedProject.id}/documentary/sources`, {
        method: "POST",
        body: JSON.stringify({
          title: researchSourceTitle,
          source_type: researchSourceType,
          creator: researchSourceCreator,
          publisher: researchSourcePublisher,
          publication_date: researchSourceDate,
          accessed_at: researchSourceAccessedAt ? new Date(researchSourceAccessedAt).toISOString() : null,
          url: researchSourceUrl.trim() || null,
          citation_text: researchSourceCitation,
          research_notes: researchSourceNotes,
        }),
      });
      setDocumentaryResearch(updated);
      setResearchSourceTitle(""); setResearchSourceType("article");
      setResearchSourceCreator(""); setResearchSourcePublisher(""); setResearchSourceDate(""); setResearchSourceAccessedAt("");
      setResearchSourceUrl(""); setResearchSourceCitation(""); setResearchSourceNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the research source.");
    } finally {
      setLoading(false);
    }
  }

  async function createDocumentaryClaim(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !claimStatement.trim()) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<DocumentaryResearch>(`/api/projects/${selectedProject.id}/documentary/claims`, {
        method: "POST",
        body: JSON.stringify({ statement: claimStatement, context: claimContext, origin: claimOrigin }),
      });
      setDocumentaryResearch(updated);
      setClaimStatement(""); setClaimContext(""); setClaimOrigin("human");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the factual claim.");
    } finally {
      setLoading(false);
    }
  }

  async function addClaimEvidence(claim: DocumentaryClaim) {
    if (!selectedProject || !evidenceSourceIds[claim.id]) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<DocumentaryResearch>(`/api/projects/${selectedProject.id}/documentary/claims/${claim.id}/evidence`, {
        method: "POST",
        body: JSON.stringify({
          source_id: evidenceSourceIds[claim.id],
          evidence_relation: evidenceRelations[claim.id] || "supports",
          excerpt: evidenceExcerpts[claim.id] || "",
          locator: evidenceLocators[claim.id] || "",
          notes: evidenceNotesByClaim[claim.id] || "",
        }),
      });
      setDocumentaryResearch(updated);
      setEvidenceSourceIds(current => ({ ...current, [claim.id]: "" }));
      setEvidenceRelations(current => ({ ...current, [claim.id]: "supports" }));
      setEvidenceExcerpts(current => ({ ...current, [claim.id]: "" }));
      setEvidenceLocators(current => ({ ...current, [claim.id]: "" }));
      setEvidenceNotesByClaim(current => ({ ...current, [claim.id]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not link evidence to the claim.");
    } finally {
      setLoading(false);
    }
  }

  async function submitClaimReview(claim: DocumentaryClaim) {
    const result = reviewResults[claim.id] || "supported";
    const rationale = reviewRationales[claim.id] || "";
    if (!selectedProject || !rationale.trim()) {
      setError("Add a rationale before submitting a fact-check decision.");
      return;
    }
    if (!window.confirm(`Record a human fact-check decision of “${result.replaceAll("_", " ")}” for this claim? The decision and current evidence snapshot will be kept in review history.`)) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<DocumentaryResearch>(`/api/projects/${selectedProject.id}/documentary/claims/${claim.id}/reviews`, {
        method: "POST",
        body: JSON.stringify({ result, rationale }),
      });
      setDocumentaryResearch(updated);
      setReviewRationales(current => ({ ...current, [claim.id]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record the fact-check review.");
    } finally {
      setLoading(false);
    }
  }

  async function updateResearchSourceStatus(source: DocumentaryResearchSource, status: "active" | "archived") {
    if (!selectedProject) return;
    if (!window.confirm(`${status === "archived" ? "Archive" : "Restore"} “${source.title}”? Existing claim citations will remain, but any current fact-check that relied on this source will need review.`)) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<DocumentaryResearch>(`/api/projects/${selectedProject.id}/documentary/sources/${source.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setDocumentaryResearch(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update research source.");
    } finally {
      setLoading(false);
    }
  }

  async function updateDocumentaryClaimStatus(claim: DocumentaryClaim, status: "active" | "archived") {
    if (!selectedProject) return;
    if (!window.confirm(`${status === "archived" ? "Archive" : "Restore"} this claim? Its evidence and fact-check history will be preserved.`)) return;
    setLoading(true);
    setError("");
    try {
      const updated = await api<DocumentaryResearch>(`/api/projects/${selectedProject.id}/documentary/claims/${claim.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setDocumentaryResearch(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update documentary claim.");
    } finally {
      setLoading(false);
    }
  }


  async function refreshDocumentaryProduction() {
    if (!selectedProject) return;
    const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/production`);
    setDocumentaryProduction(updated);
  }

  async function submitInterviewSubject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !interviewSubjectLabel.trim()) return;
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/interview-subjects`, {
        method: "POST",
        body: JSON.stringify({
          name_or_pseudonym: interviewSubjectLabel, identity_mode: interviewSubjectMode,
          role_or_relationship: interviewSubjectRole, background_notes: interviewSubjectNotes,
        }),
      });
      setDocumentaryProduction(updated);
      setInterviewSubjectLabel(""); setInterviewSubjectRole(""); setInterviewSubjectNotes(""); setInterviewSubjectMode("named");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save interview subject.");
    } finally { setLoading(false); }
  }

  async function updateInterviewSubject(subject: DocumentaryInterviewSubject, status: "active" | "archived") {
    if (!selectedProject || !window.confirm(`${status === "archived" ? "Archive" : "Restore"} ${subject.name_or_pseudonym}? Existing interview records and media references will remain.`)) return;
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/interview-subjects/${subject.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setDocumentaryProduction(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update interview subject.");
    } finally { setLoading(false); }
  }

  async function submitInterviewSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !interviewSessionSubjectId || !interviewSessionDate) return;
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/interview-sessions`, {
        method: "POST",
        body: JSON.stringify({
          subject_id: interviewSessionSubjectId,
          session_date: new Date(interviewSessionDate).toISOString(),
          interviewer_name: interviewSessionInterviewer, session_format: interviewSessionFormat,
          location_or_platform: interviewSessionLocation, transcript_notes: interviewSessionNotes,
        }),
      });
      setDocumentaryProduction(updated);
      setInterviewSessionDate(""); setInterviewSessionInterviewer(""); setInterviewSessionLocation(""); setInterviewSessionNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save interview session.");
    } finally { setLoading(false); }
  }

  async function updateInterviewSession(session: DocumentaryInterviewSession, status: "active" | "archived") {
    if (!selectedProject || !window.confirm(`${status === "archived" ? "Archive" : "Restore"} this interview session? Linked media and releases will be retained.`)) return;
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/interview-sessions/${session.id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      setDocumentaryProduction(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update interview session.");
    } finally { setLoading(false); }
  }

  function toggleReleaseUse(use: DocumentaryConsentUse) {
    setReleasePermittedUses(current => current.includes(use) ? current.filter(item => item !== use) : [...current, use]);
  }

  async function submitDocumentaryRelease(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !releaseSubjectId || !releaseConsentScope.trim()) return;
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/releases`, {
        method: "POST",
        body: JSON.stringify({
          subject_id: releaseSubjectId, interview_session_id: releaseSessionId || null,
          scope_type: releaseScopeType, scope_label: releaseScopeLabel,
          consent_scope: releaseConsentScope, withdrawal_terms: releaseWithdrawalTerms,
          permitted_uses: releasePermittedUses, status: releaseStatus,
          signed_at: releaseStatus === "signed" && releaseSignedAt ? new Date(releaseSignedAt).toISOString() : null,
          expires_at: releaseExpiresAt ? new Date(releaseExpiresAt).toISOString() : null,
          release_document_asset_id: releaseDocumentAssetId || null,
        }),
      });
      setDocumentaryProduction(updated);
      setReleaseScopeLabel(""); setReleaseConsentScope(""); setReleaseWithdrawalTerms("");
      setReleaseStatus("draft"); setReleaseSignedAt(""); setReleaseExpiresAt(""); setReleaseDocumentAssetId("");
      setReleasePermittedUses(["research", "storyboard"]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save consent release.");
    } finally { setLoading(false); }
  }

  async function withdrawDocumentaryRelease(release: DocumentaryRelease) {
    if (!selectedProject) return;
    const reason = window.prompt("Record why this consent is being withdrawn. The event will remain in the audit history.");
    if (!reason?.trim()) return;
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/releases/${release.id}/withdraw`, {
        method: "POST", body: JSON.stringify({ reason }),
      });
      setDocumentaryProduction(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not withdraw the release.");
    } finally { setLoading(false); }
  }

  async function uploadDocumentaryAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject || !documentaryUploadTitle.trim() || !documentaryUploadFile) return;
    setLoading(true); setError("");
    try {
      const body = new FormData();
      body.append("file", documentaryUploadFile, documentaryUploadFile.name);
      body.append("title", documentaryUploadTitle);
      body.append("asset_type", documentaryUploadType);
      if (documentaryUploadSourceId) body.append("source_id", documentaryUploadSourceId);
      if (documentaryUploadSessionId) body.append("interview_session_id", documentaryUploadSessionId);
      if (documentaryUploadDuration.trim()) body.append("duration_seconds", documentaryUploadDuration);
      const updated = await apiUpload<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/media`, body);
      setDocumentaryProduction(updated);
      const previousAssetIds = new Set((documentaryProduction?.media_assets || []).map(asset => asset.id));
      const newlyUploadedAsset = updated.media_assets.find(asset => !previousAssetIds.has(asset.id));
      if (newlyUploadedAsset?.asset_type === "release_document") setReleaseDocumentAssetId(newlyUploadedAsset.id);
      setDocumentaryUploadTitle(""); setDocumentaryUploadType("document"); setDocumentaryUploadSourceId("");
      setDocumentaryUploadSessionId(""); setDocumentaryUploadDuration(""); setDocumentaryUploadFile(null);
      const input = document.getElementById("documentary-media-file") as HTMLInputElement | null;
      if (input) input.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload documentary media.");
    } finally { setLoading(false); }
  }

  function mediaRightsDraft(assetId: string): DocumentaryMediaRightsDraft {
    return mediaRightsDrafts[assetId] || {
      rights_holder: "", rights_basis: "licensed", license_name: "", license_url: "",
      territory: "Worldwide", valid_from: "", valid_until: "", permitted_uses: ["research"],
      attribution_required: false, attribution_text: "", restrictions: "",
    };
  }

  function updateMediaRightsDraft(assetId: string, changes: Partial<DocumentaryMediaRightsDraft>) {
    setMediaRightsDrafts(current => {
      const existing: DocumentaryMediaRightsDraft = current[assetId] || {
        rights_holder: "", rights_basis: "licensed", license_name: "", license_url: "",
        territory: "Worldwide", valid_from: "", valid_until: "", permitted_uses: ["research"],
        attribution_required: false, attribution_text: "", restrictions: "",
      };
      return { ...current, [assetId]: { ...existing, ...changes } };
    });
  }

  function toggleMediaRightsUse(assetId: string, use: DocumentaryConsentUse) {
    setMediaRightsDrafts(current => {
      const existing: DocumentaryMediaRightsDraft = current[assetId] || {
        rights_holder: "", rights_basis: "licensed", license_name: "", license_url: "",
        territory: "Worldwide", valid_from: "", valid_until: "", permitted_uses: ["research"],
        attribution_required: false, attribution_text: "", restrictions: "",
      };
      return {
        ...current,
        [assetId]: {
          ...existing,
          permitted_uses: existing.permitted_uses.includes(use)
            ? existing.permitted_uses.filter(item => item !== use)
            : [...existing.permitted_uses, use],
        },
      };
    });
  }

  async function saveMediaRights(asset: DocumentaryMediaAsset) {
    if (!selectedProject) return;
    const draft = mediaRightsDraft(asset.id);
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/media/${asset.id}/rights`, {
        method: "POST",
        body: JSON.stringify({
          rights_holder: draft.rights_holder, rights_basis: draft.rights_basis,
          license_name: draft.license_name, license_url: draft.license_url,
          territory: draft.territory,
          valid_from: draft.valid_from ? new Date(draft.valid_from).toISOString() : null,
          valid_until: draft.valid_until ? new Date(draft.valid_until).toISOString() : null,
          permitted_uses: draft.permitted_uses,
          attribution_required: draft.attribution_required, attribution_text: draft.attribution_text,
          restrictions: draft.restrictions,
        }),
      });
      setDocumentaryProduction(updated);
      setMediaRightsDrafts(current => { const next = { ...current }; delete next[asset.id]; return next; });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save media rights.");
    } finally { setLoading(false); }
  }

  function claimUsageDraft(claimId: string): DocumentaryClaimUsageDraft {
    return claimUsageDrafts[claimId] || { usage_type: "outline", scene_id: "", script_version_id: "", reference_text: "" };
  }

  function updateClaimUsageDraft(claimId: string, changes: Partial<DocumentaryClaimUsageDraft>) {
    setClaimUsageDrafts(current => {
      const existing = current[claimId] || { usage_type: "outline", scene_id: "", script_version_id: "", reference_text: "" };
      return {
        ...current,
        [claimId]: { ...existing, ...changes, ...(changes.scene_id !== undefined ? { script_version_id: "" } : {}) },
      };
    });
  }

  async function saveClaimUsage(claim: DocumentaryClaim) {
    if (!selectedProject) return;
    const draft = claimUsageDraft(claim.id);
    setLoading(true); setError("");
    try {
      const updated = await api<DocumentaryProduction>(`/api/projects/${selectedProject.id}/documentary/claims/${claim.id}/usages`, {
        method: "POST",
        body: JSON.stringify({
          usage_type: draft.usage_type, scene_id: draft.scene_id || null,
          script_version_id: draft.script_version_id || null, reference_text: draft.reference_text,
        }),
      });
      setDocumentaryProduction(updated);
      setClaimUsageDrafts(current => ({ ...current, [claim.id]: { usage_type: "outline", scene_id: "", script_version_id: "", reference_text: "" } }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not link verified claim to production material.");
    } finally { setLoading(false); }
  }

  function showProjects() {
    setView("projects");
    setSelectedProject(null);
    setSelectedContribution(null);
    setStoryboard(null);
    setDocumentaryResearch(null);
    setDocumentaryProduction(null);
    setShowCreate(false);
    setError("");
  }

  const myMembership = selectedProject?.members.find(member => member.email === currentUser?.email);
  const canContribute = !!myMembership && myMembership.status === "active" && myMembership.role !== "viewer";
  const canEditStoryboard = canContribute && selectedProject?.current_phase === "storyboard";
  const canEditDocumentaryResearch = canContribute && selectedProject?.current_phase !== "published";
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
                    <label>Production format<select value={form.format} onChange={e => setForm({ ...form, format: e.target.value as ProjectFormat })}><option value="movie">Movie</option><option value="tv_series">TV series</option></select></label>
                    <label>Content category<select value={form.category} onChange={e => setForm({ ...form, category: e.target.value as ProjectCategory })}><option value="fiction">Fiction</option><option value="documentary">Documentary</option></select></label>
                  </div>
                  <div className="form-row">
                    <label>Genre / subject<input maxLength={80} placeholder="e.g. Drama, history, nature, science" value={form.genre} onChange={e => setForm({ ...form, genre: e.target.value })} /></label>
                    <label>Visibility<select value={form.visibility} onChange={e => setForm({ ...form, visibility: e.target.value })}><option value="private">Private · members only</option><option value="unlisted">Unlisted · link access later</option><option value="public">Public · discoverable later</option></select></label>
                  </div>
                  <label>Project description<textarea rows={3} maxLength={10000} placeholder="Set the scene. What do you want to make together?" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
                  {form.category === "documentary" && <p className="field-hint">The documentary category is available for both movies and series. Research sources, interview records, rights tracking and fact-checking are planned for a dedicated later workflow.</p>}
                  <div className="form-actions"><span>You'll be the project owner. You can invite collaborators next.</span><button className="primary-button" disabled={loading} type="submit">{loading ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />} Create project</button></div>
                </form>
              )}
              {!showCreate && projects.length === 0 && (
                <div className="empty-state"><div className="empty-icon"><FolderOpen size={25} /></div><h2>Your first story starts here.</h2><p>Create a project to give your ideas a home. You can invite collaborators as the story takes shape.</p><button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={16} /> Create your first project</button></div>
              )}
              {projects.length > 0 && <div className="project-grid">{projects.map(project => (
                <button className="project-card" key={project.id} onClick={() => openProject(project.id)}>
                  <div className="project-card-top"><span className="project-genre">{project.genre || (project.category === "documentary" ? "Documentary" : "Untitled genre")}</span><span className="project-visibility">{project.format === "tv_series" ? "TV series" : "Movie"} · {project.category}</span></div>
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
                <div className="detail-meta"><span>{selectedProject.format === "tv_series" ? "TV series" : "Movie"}</span><span>{selectedProject.category === "documentary" ? "Documentary" : "Fiction"}</span><span>{selectedProject.genre || "No genre / subject"}</span><span>{selectedProject.visibility}</span><span>Created {new Date(selectedProject.created_at).toLocaleDateString()}</span></div>
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


              {selectedProject.category === "documentary" && documentaryResearch && (
                <section className="documentary-research-section">
                  <div className="section-heading contribution-heading">
                    <div><div className="section-kicker">DOCUMENTARY WORKSPACE · M1.4</div><h2>Research & fact-checking</h2></div>
                    <span className="step-count">{documentaryResearch.sources.length} sources · {documentaryResearch.claims.length} claims</span>
                  </div>
                  <div className="documentary-integrity-note">
                    <strong>Evidence is not the same as verification.</strong>
                    <p>Record where information came from, attach exact excerpts to individual claims, and have a person review the evidence. AI-assisted claims always begin unreviewed. Every review stores its rationale and a snapshot of the evidence considered.</p>
                  </div>

                  {!canEditDocumentaryResearch && <p className="muted-note">You have read-only access to this research register, or the project has been published.</p>}

                  <div className="documentary-research-grid">
                    <section className="documentary-panel">
                      <div className="section-kicker">SOURCE REGISTER</div>
                      <h3>Research sources <span>{documentaryResearch.sources.length}</span></h3>
                      {canEditDocumentaryResearch && (
                        <form className="documentary-form" onSubmit={createResearchSource}>
                          <label>Source title<input required maxLength={240} value={researchSourceTitle} onChange={event => setResearchSourceTitle(event.target.value)} placeholder="Article, book, report, archive item…" /></label>
                          <div className="documentary-form-row">
                            <label>Source type<select value={researchSourceType} onChange={event => setResearchSourceType(event.target.value as DocumentarySourceType)}>
                              <option value="article">Article</option><option value="book">Book</option><option value="academic_paper">Academic paper</option>
                              <option value="official_record">Official record</option><option value="government_data">Government data</option>
                              <option value="interview">Interview</option><option value="archival_record">Archival record</option>
                              <option value="website">Website</option><option value="other">Other</option>
                            </select></label>
                            <label>Publication date<input maxLength={80} value={researchSourceDate} onChange={event => setResearchSourceDate(event.target.value)} placeholder="YYYY, YYYY-MM-DD or c. 1900" /></label>
                          </div>
                          <label>Accessed at<input type="datetime-local" value={researchSourceAccessedAt} onChange={event => setResearchSourceAccessedAt(event.target.value)} /><small>Leave blank to record the time this source entry is created.</small></label>
                          <div className="documentary-form-row">
                            <label>Creator / author<input maxLength={500} value={researchSourceCreator} onChange={event => setResearchSourceCreator(event.target.value)} placeholder="Author, organisation, interviewer…" /></label>
                            <label>Publisher / institution<input maxLength={240} value={researchSourcePublisher} onChange={event => setResearchSourcePublisher(event.target.value)} placeholder="Publisher or holding institution" /></label>
                          </div>
                          <label>URL<input type="url" maxLength={2048} value={researchSourceUrl} onChange={event => setResearchSourceUrl(event.target.value)} placeholder="https://…" /></label>
                          <label>Full citation<textarea rows={2} maxLength={10000} value={researchSourceCitation} onChange={event => setResearchSourceCitation(event.target.value)} placeholder="Bibliographic citation or archive reference…" /></label>
                          <label>Research notes<textarea rows={2} maxLength={10000} value={researchSourceNotes} onChange={event => setResearchSourceNotes(event.target.value)} placeholder="Context, limitations, provenance, access conditions…" /></label>
                          <button className="secondary-button" type="submit" disabled={loading || !researchSourceTitle.trim()}><Plus size={13} /> Add source</button>
                        </form>
                      )}
                      <div className="documentary-source-list">
                        {documentaryResearch.sources.map(source => (
                          <article className={source.status === "archived" ? "documentary-source-card archived" : "documentary-source-card"} key={source.id}>
                            <div className="documentary-card-heading">
                              <div><span>{source.source_type.replaceAll("_", " ").toUpperCase()} · {source.status.toUpperCase()}</span><strong>{source.title}</strong></div>
                              {canEditDocumentaryResearch && <button type="button" className="quiet-button" disabled={loading} onClick={() => updateResearchSourceStatus(source, source.status === "active" ? "archived" : "active")}>{source.status === "active" ? "Archive" : "Restore"}</button>}
                            </div>
                            {(source.creator || source.publisher || source.publication_date) && <small>{[source.creator, source.publisher, source.publication_date].filter(Boolean).join(" · ")}</small>}
                            {source.url && <a href={source.url} target="_blank" rel="noreferrer">Open source ↗</a>}
                            {source.citation_text && <p>{source.citation_text}</p>}
                            {source.research_notes && <small>Notes: {source.research_notes}</small>}
                            <small>Added {new Date(source.created_at).toLocaleDateString()} · accessed {new Date(source.accessed_at).toLocaleDateString()}</small>
                          </article>
                        ))}
                        {documentaryResearch.sources.length === 0 && <p className="muted-note">No sources registered yet. Add the first source before trying to verify a claim.</p>}
                      </div>
                    </section>

                    <section className="documentary-panel">
                      <div className="section-kicker">FACTUAL CLAIMS</div>
                      <h3>Claim ledger <span>{documentaryResearch.claims.length}</span></h3>
                      {canEditDocumentaryResearch && (
                        <form className="documentary-form" onSubmit={createDocumentaryClaim}>
                          <label>Factual claim<textarea required rows={3} maxLength={5000} value={claimStatement} onChange={event => setClaimStatement(event.target.value)} placeholder="Write one clear, testable factual statement…" /></label>
                          <label>Context / scope<textarea rows={2} maxLength={10000} value={claimContext} onChange={event => setClaimContext(event.target.value)} placeholder="Where, when and in what context does this claim apply?" /></label>
                          <label>Origin<select value={claimOrigin} onChange={event => setClaimOrigin(event.target.value as "human" | "ai_assisted")}><option value="human">Human-authored</option><option value="ai_assisted">AI-assisted · requires human review</option></select></label>
                          <button className="secondary-button" type="submit" disabled={loading || !claimStatement.trim()}><Plus size={13} /> Add claim</button>
                        </form>
                      )}
                      <div className="documentary-claim-list">
                        {documentaryResearch.claims.map(claim => (
                          <article className={claim.status === "archived" ? "documentary-claim-card archived" : "documentary-claim-card"} key={claim.id}>
                            <div className="documentary-card-heading">
                              <div><span>{claim.current_review_status.replaceAll("_", " ").toUpperCase()} · {claim.status.toUpperCase()}</span><strong>{claim.statement}</strong></div>
                              {canEditDocumentaryResearch && <button type="button" className="quiet-button" disabled={loading} onClick={() => updateDocumentaryClaimStatus(claim, claim.status === "active" ? "archived" : "active")}>{claim.status === "active" ? "Archive" : "Restore"}</button>}
                            </div>
                            <div className="documentary-claim-meta"><span>{claim.origin === "ai_assisted" ? "AI-assisted · not verified" : "Human-authored"}</span><span>Added by {claim.created_by_display_name}</span></div>
                            {claim.context && <p className="documentary-claim-context">{claim.context}</p>}

                            <div className="documentary-evidence-list">
                              <div className="section-kicker">LINKED EVIDENCE · {claim.evidence.length}</div>
                              {claim.evidence.map(evidence => (
                                <div className="documentary-evidence-card" key={evidence.id}>
                                  <strong>{evidence.source_title}</strong><span>{evidence.evidence_relation.toUpperCase()} · {evidence.source_type.replaceAll("_", " ")} · SOURCE {evidence.source_status.toUpperCase()}</span>
                                  {evidence.locator && <small>{evidence.locator}</small>}
                                  {evidence.excerpt && <blockquote>{evidence.excerpt}</blockquote>}
                                  {evidence.notes && <p>{evidence.notes}</p>}
                                </div>
                              ))}
                              {claim.evidence.length === 0 && <p className="muted-note">No sources linked. A factual review needs traceable evidence.</p>}
                            </div>

                            {canEditDocumentaryResearch && claim.status === "active" && (
                              <div className="documentary-evidence-editor">
                                <div className="section-kicker">LINK A SOURCE TO THIS CLAIM</div>
                                <label>Source<select value={evidenceSourceIds[claim.id] || ""} onChange={event => setEvidenceSourceIds(current => ({ ...current, [claim.id]: event.target.value }))}>
                                  <option value="">Choose an active source</option>
                                  {documentaryResearch.sources.filter(source => source.status === "active" && !claim.evidence.some(item => item.source_id === source.id)).map(source => <option key={source.id} value={source.id}>{source.title}</option>)}
                                </select></label>
                                <label>Evidence relationship<select value={evidenceRelations[claim.id] || "supports"} onChange={event => setEvidenceRelations(current => ({ ...current, [claim.id]: event.target.value as DocumentaryEvidenceRelation }))}>
                                  <option value="supports">Supports the claim</option><option value="challenges">Challenges the claim</option><option value="context">Provides context</option>
                                </select></label>
                                <label>Exact excerpt<textarea rows={2} maxLength={12000} value={evidenceExcerpts[claim.id] || ""} onChange={event => setEvidenceExcerpts(current => ({ ...current, [claim.id]: event.target.value }))} placeholder="Copy the relevant passage or data description…" /></label>
                                <label>Page / section / timecode<input maxLength={240} value={evidenceLocators[claim.id] || ""} onChange={event => setEvidenceLocators(current => ({ ...current, [claim.id]: event.target.value }))} placeholder="e.g. p. 42, table 3, 00:13:20" /></label>
                                <label>Evidence notes<textarea rows={2} maxLength={5000} value={evidenceNotesByClaim[claim.id] || ""} onChange={event => setEvidenceNotesByClaim(current => ({ ...current, [claim.id]: event.target.value }))} placeholder="Explain relevance, method or limitations…" /></label>
                                <button type="button" className="secondary-button" disabled={loading || !evidenceSourceIds[claim.id]} onClick={() => addClaimEvidence(claim)}>Link evidence</button>
                              </div>
                            )}

                            {canEditDocumentaryResearch && claim.status === "active" && (
                              <div className="documentary-review-editor">
                                <div className="section-kicker">HUMAN FACT-CHECK REVIEW</div>
                                <p>Submitting a review records your decision, rationale and a snapshot of all active evidence linked to this claim.</p>
                                <label>Review result<select value={reviewResults[claim.id] || "supported"} onChange={event => setReviewResults(current => ({ ...current, [claim.id]: event.target.value as DocumentaryReviewResult }))}>
                                  <option value="supported">Supported by evidence</option><option value="contested">Contested evidence</option>
                                  <option value="not_supported">Not supported</option><option value="insufficient_evidence">Insufficient evidence</option>
                                </select></label>
                                <label>Review rationale<textarea rows={2} maxLength={10000} value={reviewRationales[claim.id] || ""} onChange={event => setReviewRationales(current => ({ ...current, [claim.id]: event.target.value }))} placeholder="Explain the evidence, source quality, uncertainty and reasoning…" /></label>
                                <button type="button" className="secondary-button" disabled={loading || !(reviewRationales[claim.id] || "").trim()} onClick={() => submitClaimReview(claim)}>Record fact-check decision</button>
                              </div>
                            )}

                            <details className="documentary-review-history">
                              <summary>Review history · {claim.reviews.length}</summary>
                              {claim.reviews.length === 0 && <p className="muted-note">No human fact-check review has been recorded.</p>}
                              {[...claim.reviews].reverse().map(review => (
                                <article key={review.id}>
                                  <strong>{review.result.replaceAll("_", " ").toUpperCase()}</strong>
                                  <span>{review.reviewer_display_name} · {new Date(review.created_at).toLocaleString()}</span>
                                  <p>{review.rationale}</p>
                                  <details><summary>Evidence snapshot · {review.reviewed_evidence_snapshot.length} sources</summary>
                                    {review.reviewed_evidence_snapshot.map((item, index) => <pre key={index}>{[item.source_title, item.source_type, item.creator, item.publisher, item.publication_date, item.url, item.citation_text, item.evidence_relation, item.locator, item.excerpt, item.notes, item.accessed_at].filter(Boolean).join("\n")}</pre>)}
                                  </details>
                                </article>
                              ))}
                            </details>
                          </article>
                        ))}
                        {documentaryResearch.claims.length === 0 && <p className="muted-note">No factual claims registered yet. Split documentary narration into individual claims that can each be checked against evidence.</p>}
                      </div>
                    </section>
                  </div>
                </section>
              )}

              {selectedProject.category === "documentary" && documentaryProduction && (
                <section className="documentary-operations-section">
                  <div className="section-heading contribution-heading">
                    <div><div className="section-kicker">DOCUMENTARY WORKSPACE · M1.6</div><h2>Interviews, media & rights</h2></div>
                    <span className="step-count">{documentaryProduction.subjects.length} subjects · {documentaryProduction.sessions.length} interviews · {documentaryProduction.media_assets.length} files</span>
                  </div>
                  <div className="documentary-integrity-note">
                    <strong>Consent and rights are use-specific.</strong>
                    <p>Keep interview identity choices, session records, signed releases and media rights together. Each uploaded file receives a SHA-256 checksum and is stored privately; project membership controls access. Production placements of evidence-backed claims require a current Supported review and applicable media rights and interview consent.</p>
                  </div>

                  <div className="documentary-research-grid">
                    <section className="documentary-panel">
                      <div className="section-kicker">INTERVIEW DIRECTORY</div>
                      <h3>Interview subjects <span>{documentaryProduction.subjects.length}</span></h3>
                      {canEditDocumentaryResearch && (
                        <form className="documentary-form" onSubmit={submitInterviewSubject}>
                          <label>Name or pseudonym<input required maxLength={200} value={interviewSubjectLabel} onChange={event => setInterviewSubjectLabel(event.target.value)} placeholder="Use a pseudonym when appropriate" /></label>
                          <div className="documentary-form-row">
                            <label>Identity handling<select value={interviewSubjectMode} onChange={event => setInterviewSubjectMode(event.target.value as DocumentaryIdentityMode)}>
                              <option value="named">Named</option><option value="pseudonym">Pseudonym</option><option value="anonymous">Anonymous</option>
                            </select></label>
                            <label>Role / relationship<input maxLength={240} value={interviewSubjectRole} onChange={event => setInterviewSubjectRole(event.target.value)} placeholder="Witness, expert, family member…" /></label>
                          </div>
                          <label>Background and editorial notes<textarea rows={3} maxLength={10000} value={interviewSubjectNotes} onChange={event => setInterviewSubjectNotes(event.target.value)} /></label>
                          <button className="primary-button" type="submit" disabled={loading || !interviewSubjectLabel.trim()}><Plus size={14} /> Add subject</button>
                        </form>
                      )}
                      <div className="documentary-record-list">
                        {documentaryProduction.subjects.map(subject => (
                          <article className="documentary-record" key={subject.id}>
                            <div className="documentary-record-heading"><strong>{subject.name_or_pseudonym}</strong><span className="status-tag">{subject.identity_mode} · {subject.status}</span></div>
                            {subject.role_or_relationship && <p>{subject.role_or_relationship}</p>}
                            {subject.background_notes && <p className="muted-note">{subject.background_notes}</p>}
                            {canEditDocumentaryResearch && <button type="button" className="quiet-button" onClick={() => updateInterviewSubject(subject, subject.status === "active" ? "archived" : "active")}>{subject.status === "active" ? "Archive subject" : "Restore subject"}</button>}
                          </article>
                        ))}
                        {documentaryProduction.subjects.length === 0 && <p className="muted-note">Add a subject before registering an interview.</p>}
                      </div>
                    </section>

                    <section className="documentary-panel">
                      <div className="section-kicker">INTERVIEW SESSIONS</div>
                      <h3>Sessions <span>{documentaryProduction.sessions.length}</span></h3>
                      {canEditDocumentaryResearch && (
                        <form className="documentary-form" onSubmit={submitInterviewSession}>
                          <label>Subject<select required value={interviewSessionSubjectId} onChange={event => setInterviewSessionSubjectId(event.target.value)}>
                            <option value="">Choose an active subject</option>
                            {documentaryProduction.subjects.filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>{item.name_or_pseudonym}</option>)}
                          </select></label>
                          <label>Date and time<input required type="datetime-local" value={interviewSessionDate} onChange={event => setInterviewSessionDate(event.target.value)} /></label>
                          <div className="documentary-form-row">
                            <label>Format<select value={interviewSessionFormat} onChange={event => setInterviewSessionFormat(event.target.value)}>
                              <option value="in_person">In person</option><option value="remote">Remote</option><option value="phone">Phone</option><option value="written">Written</option><option value="other">Other</option>
                            </select></label>
                            <label>Interviewer<input maxLength={200} value={interviewSessionInterviewer} onChange={event => setInterviewSessionInterviewer(event.target.value)} /></label>
                          </div>
                          <label>Location / platform<input maxLength={240} value={interviewSessionLocation} onChange={event => setInterviewSessionLocation(event.target.value)} /></label>
                          <label>Transcript reference and session notes<textarea rows={3} maxLength={20000} value={interviewSessionNotes} onChange={event => setInterviewSessionNotes(event.target.value)} /></label>
                          <button className="primary-button" type="submit" disabled={loading || !interviewSessionSubjectId || !interviewSessionDate}><Plus size={14} /> Add interview session</button>
                        </form>
                      )}
                      <div className="documentary-record-list">
                        {documentaryProduction.sessions.map(session => (
                          <article className="documentary-record" key={session.id}>
                            <div className="documentary-record-heading"><strong>{session.subject_label}</strong><span className="status-tag">{session.status}</span></div>
                            <p>{new Date(session.session_date).toLocaleString()} · {session.session_format.replace("_", " ")}{session.interviewer_name ? ` · Interviewer: ${session.interviewer_name}` : ""}</p>
                            {session.location_or_platform && <p className="muted-note">{session.location_or_platform}</p>}
                            {session.transcript_notes && <p>{session.transcript_notes}</p>}
                            <small>{session.media_asset_ids.length} linked file(s)</small>
                            {canEditDocumentaryResearch && <button type="button" className="quiet-button" onClick={() => updateInterviewSession(session, session.status === "active" ? "archived" : "active")}>{session.status === "active" ? "Archive session" : "Restore session"}</button>}
                          </article>
                        ))}
                        {documentaryProduction.sessions.length === 0 && <p className="muted-note">No interview sessions have been registered.</p>}
                      </div>
                    </section>
                  </div>

                  <div className="documentary-panel documentary-wide-panel">
                    <div className="section-kicker">RELEASES & CONSENT</div>
                    <h3>Participant releases <span>{documentaryProduction.releases.length}</span></h3>
                    <p className="muted-note">A draft is not proof of consent. A signed record captures the signing date, scope, permitted uses, expiry and withdrawal terms. Withdrawal is an audited event and immediately blocks later use through this workflow.</p>
                    {canEditDocumentaryResearch && (
                      <form className="documentary-form" onSubmit={submitDocumentaryRelease}>
                        <div className="documentary-form-row">
                          <label>Subject<select required value={releaseSubjectId} onChange={event => setReleaseSubjectId(event.target.value)}>
                            <option value="">Choose subject</option>
                            {documentaryProduction.subjects.filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>{item.name_or_pseudonym}</option>)}
                          </select></label>
                          <label>Interview session (optional)<select value={releaseSessionId} onChange={event => setReleaseSessionId(event.target.value)}>
                            <option value="">All qualifying sessions for this subject</option>
                            {documentaryProduction.sessions.filter(item => item.status === "active" && (!releaseSubjectId || item.subject_id === releaseSubjectId)).map(item => <option key={item.id} value={item.id}>{new Date(item.session_date).toLocaleDateString()} · {item.subject_label}</option>)}
                          </select></label>
                          <label>Consent scope<select value={releaseScopeType} onChange={event => setReleaseScopeType(event.target.value as "project" | "production" | "release")}>
                            <option value="project">Project</option><option value="production">Production</option><option value="release">Named release</option>
                          </select></label>
                        </div>
                        {releaseScopeType === "release" && <label>Release / usage label<input required maxLength={240} value={releaseScopeLabel} onChange={event => setReleaseScopeLabel(event.target.value)} placeholder="Name the specific release or use" /></label>}
                        <label>What has the participant consented to?<textarea required rows={3} maxLength={10000} value={releaseConsentScope} onChange={event => setReleaseConsentScope(event.target.value)} placeholder="Describe the interview, recording, editing and identification scope…" /></label>
                        <label>Withdrawal terms<textarea rows={2} maxLength={10000} value={releaseWithdrawalTerms} onChange={event => setReleaseWithdrawalTerms(event.target.value)} placeholder="Describe how withdrawal requests are handled and any limitations…" /></label>
                        <div className="documentary-use-grid">
                          {documentaryUseOptions.map(option => <label className="documentary-use-option" key={option.value}><input type="checkbox" checked={releasePermittedUses.includes(option.value)} onChange={() => toggleReleaseUse(option.value)} /> {option.label}</label>)}
                        </div>
                        <div className="documentary-form-row">
                          <label>Record state<select value={releaseStatus} onChange={event => setReleaseStatus(event.target.value as "draft" | "signed")}><option value="draft">Draft / not signed</option><option value="signed">Signed</option></select></label>
                          {releaseStatus === "signed" && <label>Signed at<input required type="datetime-local" value={releaseSignedAt} onChange={event => setReleaseSignedAt(event.target.value)} /></label>}
                          <label>Expires at (optional)<input type="datetime-local" value={releaseExpiresAt} onChange={event => setReleaseExpiresAt(event.target.value)} /></label>
                          <label>Signed document (optional)<select value={releaseDocumentAssetId} onChange={event => setReleaseDocumentAssetId(event.target.value)}><option value="">No uploaded document</option>{documentaryProduction.media_assets.filter(item => item.asset_type === "release_document" && item.status === "active").map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
                        </div>
                        <button className="primary-button" type="submit" disabled={loading || !releaseSubjectId || !releaseConsentScope.trim() || (releaseStatus === "signed" && !releaseSignedAt) || (releaseScopeType === "release" && !releaseScopeLabel.trim())}><Plus size={14} /> Save release record</button>
                      </form>
                    )}
                    <div className="documentary-record-list documentary-record-list-wide">
                      {documentaryProduction.releases.map(release => (
                        <article className="documentary-record" key={release.id}>
                          <div className="documentary-record-heading"><strong>{release.subject_label} · {release.scope_type}{release.scope_label ? ` · ${release.scope_label}` : ""}</strong><span className={release.status === "signed" ? "status-tag verified" : "status-tag"}>{release.status}</span></div>
                          <p>{release.consent_scope}</p>
                          <small>Permitted: {release.permitted_uses.map(use => use.replace("_", " ")).join(", ") || "No uses selected"}{release.signed_at ? ` · Signed ${new Date(release.signed_at).toLocaleDateString()}` : ""}{release.expires_at ? ` · Expires ${new Date(release.expires_at).toLocaleDateString()}` : ""}</small>
                          {release.withdrawal_terms && <p className="muted-note">Withdrawal: {release.withdrawal_terms}</p>}
                          {release.release_document_asset_id && <small>Signed document attached · accessible to owners and editors only</small>}
                          {release.events.length > 0 && <details><summary>Consent audit history ({release.events.length})</summary>{release.events.map(item => <p key={item.id}><small>{item.previous_status || "new"} → {item.new_status} · {new Date(item.created_at).toLocaleString()} · {item.reason}</small></p>)}</details>}
                          {canEditDocumentaryResearch && release.status !== "withdrawn" && <button type="button" className="quiet-button danger-button" onClick={() => withdrawDocumentaryRelease(release)}>Record withdrawal</button>}
                        </article>
                      ))}
                      {documentaryProduction.releases.length === 0 && <p className="muted-note">No releases have been recorded yet.</p>}
                    </div>
                  </div>

                  <div className="documentary-research-grid">
                    <section className="documentary-panel">
                      <div className="section-kicker">PRIVATE SOURCE FILES</div>
                      <h3>Upload media <span>{documentaryProduction.media_assets.length}</span></h3>
                      <p className="muted-note">Maximum 100 MiB per file. Accepted formats include PDF, text, CSV, JSON, DOCX/ODT, common audio/video and image files. Files are not served from a public URL.</p>
                      {canEditDocumentaryResearch && (
                        <form className="documentary-form" onSubmit={uploadDocumentaryAsset}>
                          <label>Asset title<input required maxLength={240} value={documentaryUploadTitle} onChange={event => setDocumentaryUploadTitle(event.target.value)} /></label>
                          <div className="documentary-form-row">
                            <label>Asset type<select value={documentaryUploadType} onChange={event => setDocumentaryUploadType(event.target.value)}>
                              <option value="document">Document</option><option value="transcript">Transcript</option><option value="audio">Audio</option>
                              <option value="video">Video</option><option value="image">Image</option><option value="release_document">Signed release document</option><option value="other">Other</option>
                            </select></label>
                            <label>Duration in seconds<input type="number" min="1" value={documentaryUploadDuration} onChange={event => setDocumentaryUploadDuration(event.target.value)} placeholder="Optional" /></label>
                          </div>
                          <label>Research source (optional)<select value={documentaryUploadSourceId} onChange={event => setDocumentaryUploadSourceId(event.target.value)}><option value="">Not linked to a source</option>{(documentaryResearch?.sources || []).filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
                          <label>Interview session (optional)<select value={documentaryUploadSessionId} onChange={event => setDocumentaryUploadSessionId(event.target.value)}><option value="">Not linked to an interview</option>{documentaryProduction.sessions.filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>{item.subject_label} · {new Date(item.session_date).toLocaleDateString()}</option>)}</select></label>
                          <label>File<input id="documentary-media-file" required type="file" onChange={event => setDocumentaryUploadFile(event.target.files?.[0] || null)} /></label>
                          <button className="primary-button" type="submit" disabled={loading || !documentaryUploadTitle.trim() || !documentaryUploadFile}><Plus size={14} /> Upload private file</button>
                        </form>
                      )}
                    </section>

                    <section className="documentary-panel">
                      <div className="section-kicker">PROVENANCE & LICENSING</div>
                      <h3>Media assets <span>{documentaryProduction.media_assets.length}</span></h3>
                      <div className="documentary-record-list">
                        {documentaryProduction.media_assets.map(asset => {
                          const rightsDraft = mediaRightsDraft(asset.id);
                          return (
                            <article className="documentary-record" key={asset.id}>
                              <div className="documentary-record-heading"><strong>{asset.title}</strong><span className="status-tag">{asset.asset_type} · {asset.status}</span></div>
                              <p>{asset.original_filename} · {(asset.size_bytes / 1024 / 1024).toFixed(2)} MiB{asset.duration_seconds ? ` · ${asset.duration_seconds}s` : ""}</p>
                              <small>SHA-256: {asset.sha256}</small>
                              <div><a className="text-link" href={asset.download_url} target="_blank" rel="noreferrer"><ArrowUpRight size={13} /> Download private file</a></div>
                              {asset.latest_rights && <p className="muted-note">Rights v{asset.latest_rights.version_number}: {asset.latest_rights.rights_basis.replace("_", " ")} · {asset.latest_rights.rights_holder || "Rights holder not recorded"} · {asset.latest_rights.territory} · {asset.latest_rights.status}. Permitted: {asset.latest_rights.permitted_uses.join(", ") || "none"}.</p>}
                              {canEditDocumentaryResearch && (
                                <details className="rights-editor">
                                  <summary>{asset.latest_rights ? "Create a new rights version" : "Add rights / provenance record"}</summary>
                                  <div className="documentary-form">
                                    <label>Rights holder<input maxLength={240} value={rightsDraft.rights_holder} onChange={event => updateMediaRightsDraft(asset.id, { rights_holder: event.target.value })} /></label>
                                    <div className="documentary-form-row">
                                      <label>Rights basis<select value={rightsDraft.rights_basis} onChange={event => updateMediaRightsDraft(asset.id, { rights_basis: event.target.value })}>
                                        <option value="owned">Owned by project</option><option value="licensed">Licensed</option><option value="public_domain">Public domain</option><option value="permission">Explicit permission</option><option value="fair_use">Fair use / exception claim</option><option value="research_only">Research only</option><option value="unknown">Unknown / unresolved</option>
                                      </select></label>
                                      <label>Territory<input required maxLength={240} value={rightsDraft.territory} onChange={event => updateMediaRightsDraft(asset.id, { territory: event.target.value })} /></label>
                                    </div>
                                    {rightsDraft.rights_basis === "licensed" && <label>Licence name<input required maxLength={240} value={rightsDraft.license_name} onChange={event => updateMediaRightsDraft(asset.id, { license_name: event.target.value })} /></label>}
                                    <label>Licence / permission URL<input maxLength={2048} value={rightsDraft.license_url} onChange={event => updateMediaRightsDraft(asset.id, { license_url: event.target.value })} /></label>
                                    <div className="documentary-form-row">
                                      <label>Rights valid from (optional)<input type="datetime-local" value={rightsDraft.valid_from} onChange={event => updateMediaRightsDraft(asset.id, { valid_from: event.target.value })} /></label>
                                      <label>Rights valid until (optional)<input type="datetime-local" value={rightsDraft.valid_until} onChange={event => updateMediaRightsDraft(asset.id, { valid_until: event.target.value })} /></label>
                                    </div>
                                    <div className="documentary-use-grid">
                                      {documentaryUseOptions.map(option => <label className="documentary-use-option" key={option.value}><input type="checkbox" checked={rightsDraft.permitted_uses.includes(option.value)} onChange={() => toggleMediaRightsUse(asset.id, option.value)} /> {option.label}</label>)}
                                    </div>
                                    <label className="documentary-use-option"><input type="checkbox" checked={rightsDraft.attribution_required} onChange={event => updateMediaRightsDraft(asset.id, { attribution_required: event.target.checked })} /> Attribution required</label>
                                    {rightsDraft.attribution_required && <label>Required attribution text<textarea rows={2} value={rightsDraft.attribution_text} onChange={event => updateMediaRightsDraft(asset.id, { attribution_text: event.target.value })} /></label>}
                                    <label>Restrictions and provenance notes<textarea rows={2} value={rightsDraft.restrictions} onChange={event => updateMediaRightsDraft(asset.id, { restrictions: event.target.value })} /></label>
                                    <button type="button" className="primary-button" disabled={loading || !rightsDraft.territory.trim() || (rightsDraft.rights_basis === "licensed" && !rightsDraft.license_name.trim())} onClick={() => saveMediaRights(asset)}>Save rights version</button>
                                  </div>
                                </details>
                              )}
                            </article>
                          );
                        })}
                        {documentaryProduction.media_assets.length === 0 && <p className="muted-note">No source files have been uploaded.</p>}
                      </div>
                    </section>
                  </div>

                  <div className="documentary-panel documentary-wide-panel">
                    <div className="section-kicker">CLAIM-TO-PRODUCTION REFERENCES</div>
                    <h3>Place verified claims <span>{documentaryProduction.claim_usages.length}</span></h3>
                    <p className="muted-note">Only claims with a current Supported human review can be placed. Each placement is append-only and points to the relevant outline, scene, or exact screenplay revision. For uploaded evidence, the required use must be allowed by the latest rights record and, for interview files, by a current signed release.</p>
                    <div className="documentary-record-list documentary-record-list-wide">
                      {(documentaryResearch?.claims || []).filter(claim => claim.status === "active").map(claim => {
                        const usage = claimUsageDraft(claim.id);
                        const targetScene = storyboard?.scenes.find(scene => scene.id === usage.scene_id);
                        const needsScene = ["scene", "script", "lower_third", "caption", "narration"].includes(usage.usage_type);
                        return (
                          <article className="documentary-record" key={claim.id}>
                            <div className="documentary-record-heading"><strong>{claim.statement}</strong><span className={claim.current_review_status === "supported" ? "status-tag verified" : "status-tag"}>{claim.current_review_status.replace("_", " ")}</span></div>
                            {claim.current_review_status === "supported" && canEditDocumentaryResearch && (
                              <div className="documentary-form claim-usage-form">
                                <div className="documentary-form-row">
                                  <label>Place in<select value={usage.usage_type} onChange={event => updateClaimUsageDraft(claim.id, { usage_type: event.target.value, scene_id: "", script_version_id: "" })}>
                                    <option value="outline">Documentary outline / research notes</option><option value="scene">Scene</option><option value="script">Exact screenplay revision</option>
                                    <option value="narration">Narration</option><option value="lower_third">Lower third</option><option value="caption">Caption</option>
                                  </select></label>
                                  {needsScene && <label>Scene<select value={usage.scene_id} onChange={event => updateClaimUsageDraft(claim.id, { scene_id: event.target.value })}><option value="">Choose scene</option>{(storyboard?.scenes || []).map(scene => <option key={scene.id} value={scene.id}>{scene.scene_order}. {scene.title}</option>)}</select></label>}
                                  {usage.usage_type === "script" && targetScene && <label>Screenplay revision<select value={usage.script_version_id} onChange={event => updateClaimUsageDraft(claim.id, { script_version_id: event.target.value })}><option value="">Choose exact revision</option>{targetScene.script_versions.map(version => <option key={version.id} value={version.id}>Revision {version.revision_number}</option>)}</select></label>}
                                </div>
                                <label>Placement note / wording<textarea rows={2} maxLength={10000} value={usage.reference_text} onChange={event => updateClaimUsageDraft(claim.id, { reference_text: event.target.value })} placeholder="Describe how this verified claim is used…" /></label>
                                <button type="button" className="primary-button" disabled={loading || (needsScene && !usage.scene_id) || (usage.usage_type === "script" && !usage.script_version_id)} onClick={() => saveClaimUsage(claim)}><Plus size={14} /> Add production reference</button>
                              </div>
                            )}
                            {claim.current_review_status !== "supported" && <p className="muted-note">This claim must have a current Supported human review before it can be linked to production material.</p>}
                          </article>
                        );
                      })}
                    </div>
                    <h4>Existing placements</h4>
                    <div className="documentary-record-list documentary-record-list-wide">
                      {documentaryProduction.claim_usages.map(usage => (
                        <article className="documentary-record" key={usage.id}>
                          <div className="documentary-record-heading"><strong>{usage.usage_type.replace("_", " ")}{usage.scene_title ? ` · ${usage.scene_title}` : ""}{usage.script_revision_number ? ` · screenplay rev ${usage.script_revision_number}` : ""}</strong><span className="status-tag verified">{usage.claim_review_status}</span></div>
                          <p>{usage.claim_statement}</p>{usage.reference_text && <small>{usage.reference_text}</small>}
                          <small>Linked {new Date(usage.created_at).toLocaleString()} · immutable reference</small>
                        </article>
                      ))}
                      {documentaryProduction.claim_usages.length === 0 && <p className="muted-note">No claims have been placed in outlines, scenes, scripts, narration, lower thirds or captions.</p>}
                    </div>
                  </div>
                </section>
              )}

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

              {(selectedProject.current_phase === "storyboard" || storyboard !== null) && (
                <section className="storyboard-section">
                  <div className="section-heading contribution-heading">
                    <div><div className="section-kicker">M1 · STORYBOARD & CREATIVE ASSETS</div><h2>{selectedProject.format === "tv_series" ? "Build the series, episode by episode." : selectedProject.category === "documentary" ? "Shape the documentary, scene by scene." : "Build the film, scene by scene."}</h2></div>
                    <span className="step-count">{storyboard ? `${storyboard.scenes.length} scenes` : "Ready to initialize"}</span>
                  </div>
                  {!storyboard ? (
                    <div className="storyboard-empty">
                      <p>The narrative is approved. Initialize a storyboard anchored to that exact immutable version before adding scenes, characters or locations.</p>
                      {canEditStoryboard
                        ? <button className="primary-button" type="button" disabled={loading} onClick={initializeStoryboard}><Clapperboard size={15} /> Initialize storyboard</button>
                        : <p className="muted-note">A project owner, editor or contributor can initialize the storyboard. You have read-only access.</p>}
                    </div>
                  ) : (
                    <>
                      <div className="storyboard-source-card">
                        <div><div className="section-kicker">APPROVED NARRATIVE · IMMUTABLE SOURCE</div><strong>{storyboard.narrative_title} · Version {storyboard.narrative_version_number}</strong><p>The storyboard remains linked to this approved version, even if the project evolves later.</p></div>
                        {selectedProject.current_phase !== "storyboard" && <p className="muted-note">This project has moved beyond storyboarding. The storyboard remains available as a read-only record.</p>}
                        <span className="approval-status approved">Approved</span>
                      </div>

                      <details className="storyboard-narrative-source">
                        <summary>Read / copy from the approved narrative ({storyboard.narrative_content.length.toLocaleString()} characters)</summary>
                        <pre>{storyboard.narrative_content}</pre>
                        <small>To connect a scene to its source, copy an exact passage from here and paste it into that scene's passage-link form.</small>
                      </details>

                      {selectedProject.format === "tv_series" && (
                        <section className="series-structure-panel">
                          <div className="section-heading">
                            <div><div className="section-kicker">SERIES STRUCTURE</div><h2>Seasons & episodes <span className="contribution-count">{storyboard.seasons.length}</span></h2></div>
                            <span className="step-count">Each episode has its own scene sequence and screenplay.</span>
                          </div>
                          {canEditStoryboard && (
                            <div className="series-forms-grid">
                              <form className="storyboard-mini-form" onSubmit={submitSeason}>
                                <h3>Create a season</h3>
                                <div className="storyboard-scene-form-row">
                                  <label>Season number<input type="number" min="1" max="100" required value={seasonNumber} onChange={event => setSeasonNumber(event.target.value)} /></label>
                                  <label>Season title<input required maxLength={160} value={seasonTitle} onChange={event => setSeasonTitle(event.target.value)} placeholder="e.g. The Beginning" /></label>
                                </div>
                                <label>Description<textarea rows={2} maxLength={10000} value={seasonDescription} onChange={event => setSeasonDescription(event.target.value)} placeholder="What defines this season?" /></label>
                                <label>Season story arc<textarea rows={3} maxLength={10000} value={seasonStoryArc} onChange={event => setSeasonStoryArc(event.target.value)} placeholder="The larger narrative movement across the season…" /></label>
                                <button className="secondary-button" type="submit" disabled={loading || !seasonTitle.trim()}><Plus size={13} /> Add season</button>
                              </form>
                              <form className="storyboard-mini-form" onSubmit={submitEpisode}>
                                <h3>Create an episode</h3>
                                <label>Season<select required value={episodeSeasonId} onChange={event => setEpisodeSeasonId(event.target.value)}>
                                  <option value="">Select a season</option>
                                  {storyboard.seasons.filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>Season {item.season_number} · {item.title}</option>)}
                                </select></label>
                                <div className="storyboard-scene-form-row">
                                  <label>Episode number<input type="number" min="1" max="1000" required value={episodeNumber} onChange={event => setEpisodeNumber(event.target.value)} /></label>
                                  <label>Episode title<input required maxLength={160} value={episodeTitle} onChange={event => setEpisodeTitle(event.target.value)} placeholder="Episode title" /></label>
                                </div>
                                <label>Logline<input maxLength={500} value={episodeLogline} onChange={event => setEpisodeLogline(event.target.value)} placeholder="A one-sentence episode hook" /></label>
                                <label>Synopsis<textarea rows={2} maxLength={10000} value={episodeSynopsis} onChange={event => setEpisodeSynopsis(event.target.value)} placeholder="What happens in this episode?" /></label>
                                <label>Estimated runtime (seconds)<input type="number" min="1" max="86400" value={episodeDuration} onChange={event => setEpisodeDuration(event.target.value)} placeholder="e.g. 2700" /></label>
                                <button className="secondary-button" type="submit" disabled={loading || !episodeSeasonId || !episodeTitle.trim()}><Plus size={13} /> Add episode</button>
                              </form>
                            </div>
                          )}
                          <div className="series-season-list">
                            {storyboard.seasons.map(season => (
                              <article className={season.status === "archived" ? "series-season-card archived" : "series-season-card"} key={season.id}>
                                <div className="series-season-heading">
                                  <div><span>SEASON {season.season_number} · {season.status.toUpperCase()}</span><strong>{season.title}</strong></div>
                                  {canEditStoryboard && <button type="button" className="quiet-button" onClick={() => updateSeasonStatus(season, season.status === "active" ? "archived" : "active")}>{season.status === "active" ? "Archive season" : "Restore season"}</button>}
                                </div>
                                {season.description && <p>{season.description}</p>}
                                {season.story_arc && <div className="series-story-arc"><strong>SEASON ARC</strong><p>{season.story_arc}</p></div>}
                                <div className="series-episode-list">
                                  {season.episodes.map(episode => (
                                    <article className={episode.status === "archived" ? "series-episode-card archived" : "series-episode-card"} key={episode.id}>
                                      <div>
                                        <span>EPISODE {episode.episode_number} · {episode.status.toUpperCase()}{episode.estimated_duration_seconds ? ` · EST. ${Math.round(episode.estimated_duration_seconds / 60)} MIN` : ""}</span>
                                        <strong>{episode.title}</strong>
                                        {episode.logline && <small>{episode.logline}</small>}
                                        {episode.synopsis && <p>{episode.synopsis}</p>}
                                      </div>
                                      {canEditStoryboard && <button type="button" className="quiet-button" onClick={() => updateEpisodeStatus(episode, episode.status === "active" ? "archived" : "active")}>{episode.status === "active" ? "Archive" : "Restore"}</button>}
                                    </article>
                                  ))}
                                  {season.episodes.length === 0 && <p className="muted-note">No episodes in this season yet.</p>}
                                </div>
                              </article>
                            ))}
                            {storyboard.seasons.length === 0 && <p className="muted-note">Start by creating Season 1, then add its episodes. Scenes are attached to an episode rather than a project-wide sequence.</p>}
                          </div>
                        </section>
                      )}

                      <div className="storyboard-assets-grid">
                        <section className="storyboard-asset-panel">
                          <div className="section-kicker">CHARACTER DIRECTORY</div>
                          <h3>Characters <span>{storyboard.characters.length}</span></h3>
                          {canEditStoryboard && (
                            <form className="storyboard-mini-form" onSubmit={submitCharacter}>
                              <label>Name<input required maxLength={160} value={characterName} onChange={event => setCharacterName(event.target.value)} placeholder="Character name" /></label>
                              <label>Story description<textarea rows={2} maxLength={10000} value={characterDescription} onChange={event => setCharacterDescription(event.target.value)} placeholder="Who are they in the story?" /></label>
                              <label>Visual description<textarea rows={2} maxLength={10000} value={characterVisual} onChange={event => setCharacterVisual(event.target.value)} placeholder="Appearance, clothing, distinguishing features…" /></label>
                              <label>Personality notes<textarea rows={2} maxLength={10000} value={characterPersonality} onChange={event => setCharacterPersonality(event.target.value)} placeholder="Traits, motivations, mannerisms…" /></label>
                              <button className="secondary-button" type="submit" disabled={loading || !characterName.trim()}><Plus size={13} /> Add character</button>
                            </form>
                          )}
                          <div className="storyboard-asset-list">
                            {storyboard.characters.filter(item => item.status === "active").map(character => {
                              const edit = characterEditDraft(character);
                              return (
                                <article className="storyboard-asset" key={character.id}>
                                  <div className="storyboard-asset-heading"><strong>{character.name}</strong><span>ACTIVE</span></div>
                                  {character.description && <p>{character.description}</p>}
                                  {character.visual_description && <small>Visual: {character.visual_description}</small>}
                                  {character.personality_notes && <small>Personality: {character.personality_notes}</small>}
                                  {canEditStoryboard && (
                                    <details className="story-bible-edit">
                                      <summary>Edit character profile</summary>
                                      <form className="storyboard-mini-form" onSubmit={event => { event.preventDefault(); saveCharacterDetails(character); }}>
                                        <label>Name<input required maxLength={160} value={edit.name} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, name: event.target.value } }))} /></label>
                                        <label>Story description<textarea rows={3} maxLength={10000} value={edit.description} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, description: event.target.value } }))} /></label>
                                        <label>Visual description<textarea rows={3} maxLength={10000} value={edit.visual_description} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, visual_description: event.target.value } }))} /></label>
                                        <label>Personality notes<textarea rows={3} maxLength={10000} value={edit.personality_notes} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, personality_notes: event.target.value } }))} /></label>
                                        <div className="story-bible-edit-actions">
                                          <button className="secondary-button" type="submit" disabled={loading || !edit.name.trim()}>Save profile</button>
                                          <button className="quiet-button" type="button" onClick={() => setCharacterEdits(current => { const next = { ...current }; delete next[character.id]; return next; })}>Reset draft</button>
                                        </div>
                                      </form>
                                    </details>
                                  )}
                                  {canEditStoryboard && <button type="button" className="quiet-button danger-button" disabled={loading} onClick={() => updateCharacterStatus(character, "archived")}>Archive character</button>}
                                </article>
                              );
                            })}
                            {storyboard.characters.filter(item => item.status === "active").length === 0 && <p className="muted-note">No active characters yet.</p>}
                            {storyboard.characters.some(item => item.status === "archived") && (
                              <details className="story-bible-archive-list" open={showArchivedCharacters} onToggle={event => setShowArchivedCharacters(event.currentTarget.open)}>
                                <summary>Archived characters · {storyboard.characters.filter(item => item.status === "archived").length}</summary>
                                {storyboard.characters.filter(item => item.status === "archived").map(character => {
                                  const edit = characterEditDraft(character);
                                  return (
                                    <article className="storyboard-asset archived" key={character.id}>
                                      <div className="storyboard-asset-heading"><strong>{character.name}</strong><span>ARCHIVED</span></div>
                                      {character.description && <p>{character.description}</p>}
                                      {character.visual_description && <small>Visual: {character.visual_description}</small>}
                                      {character.personality_notes && <small>Personality: {character.personality_notes}</small>}
                                      {canEditStoryboard && (
                                        <details className="story-bible-edit">
                                          <summary>Edit archived profile</summary>
                                          <form className="storyboard-mini-form" onSubmit={event => { event.preventDefault(); saveCharacterDetails(character); }}>
                                            <label>Name<input required maxLength={160} value={edit.name} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, name: event.target.value } }))} /></label>
                                            <label>Story description<textarea rows={3} maxLength={10000} value={edit.description} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, description: event.target.value } }))} /></label>
                                            <label>Visual description<textarea rows={3} maxLength={10000} value={edit.visual_description} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, visual_description: event.target.value } }))} /></label>
                                            <label>Personality notes<textarea rows={3} maxLength={10000} value={edit.personality_notes} onChange={event => setCharacterEdits(current => ({ ...current, [character.id]: { ...edit, personality_notes: event.target.value } }))} /></label>
                                            <button className="secondary-button" type="submit" disabled={loading || !edit.name.trim()}>Save profile</button>
                                          </form>
                                        </details>
                                      )}
                                      {canEditStoryboard && <button type="button" className="secondary-button" disabled={loading} onClick={() => updateCharacterStatus(character, "active")}>Restore character</button>}
                                    </article>
                                  );
                                })}
                              </details>
                            )}
                          </div>
                        </section>

                        <section className="storyboard-asset-panel">
                          <div className="section-kicker">LOCATION DIRECTORY</div>
                          <h3>Locations <span>{storyboard.locations.length}</span></h3>
                          {canEditStoryboard && (
                            <form className="storyboard-mini-form" onSubmit={submitLocation}>
                              <label>Name<input required maxLength={160} value={locationName} onChange={event => setLocationName(event.target.value)} placeholder="Location name" /></label>
                              <label>Environment
                                <select value={locationType} onChange={event => setLocationType(event.target.value)}>
                                  <option value="interior">Interior</option><option value="exterior">Exterior</option>
                                  <option value="vehicle">Vehicle</option><option value="virtual">Virtual / imagined</option>
                                  <option value="unspecified">Unspecified</option>
                                </select>
                              </label>
                              <label>Time period<input maxLength={120} value={locationPeriod} onChange={event => setLocationPeriod(event.target.value)} placeholder="e.g. Present day, 1920s…" /></label>
                              <label>Description<textarea rows={2} maxLength={10000} value={locationDescription} onChange={event => setLocationDescription(event.target.value)} placeholder="What is this place?" /></label>
                              <label>Visual notes<textarea rows={2} maxLength={10000} value={locationVisual} onChange={event => setLocationVisual(event.target.value)} placeholder="Mood, architecture, light, atmosphere…" /></label>
                              <button className="secondary-button" type="submit" disabled={loading || !locationName.trim()}><Plus size={13} /> Add location</button>
                            </form>
                          )}
                          <div className="storyboard-asset-list">
                            {storyboard.locations.filter(item => item.status === "active").map(location => {
                              const edit = locationEditDraft(location);
                              return (
                                <article className="storyboard-asset" key={location.id}>
                                  <div className="storyboard-asset-heading"><strong>{location.name}</strong><span>{location.environment_type} · ACTIVE</span></div>
                                  {location.time_period && <small>{location.time_period}</small>}
                                  {location.description && <p>{location.description}</p>}
                                  {location.visual_notes && <small>Visual: {location.visual_notes}</small>}
                                  {canEditStoryboard && (
                                    <details className="story-bible-edit">
                                      <summary>Edit location profile</summary>
                                      <form className="storyboard-mini-form" onSubmit={event => { event.preventDefault(); saveLocationDetails(location); }}>
                                        <label>Name<input required maxLength={160} value={edit.name} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, name: event.target.value } }))} /></label>
                                        <label>Environment<select value={edit.environment_type} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, environment_type: event.target.value } }))}>
                                          <option value="interior">Interior</option><option value="exterior">Exterior</option><option value="vehicle">Vehicle</option><option value="virtual">Virtual / imagined</option><option value="unspecified">Unspecified</option>
                                        </select></label>
                                        <label>Time period<input maxLength={120} value={edit.time_period} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, time_period: event.target.value } }))} /></label>
                                        <label>Description<textarea rows={3} maxLength={10000} value={edit.description} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, description: event.target.value } }))} /></label>
                                        <label>Visual notes<textarea rows={3} maxLength={10000} value={edit.visual_notes} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, visual_notes: event.target.value } }))} /></label>
                                        <div className="story-bible-edit-actions">
                                          <button className="secondary-button" type="submit" disabled={loading || !edit.name.trim()}>Save profile</button>
                                          <button className="quiet-button" type="button" onClick={() => setLocationEdits(current => { const next = { ...current }; delete next[location.id]; return next; })}>Reset draft</button>
                                        </div>
                                      </form>
                                    </details>
                                  )}
                                  {canEditStoryboard && <button type="button" className="quiet-button danger-button" disabled={loading} onClick={() => updateLocationStatus(location, "archived")}>Archive location</button>}
                                </article>
                              );
                            })}
                            {storyboard.locations.filter(item => item.status === "active").length === 0 && <p className="muted-note">No active locations yet.</p>}
                            {storyboard.locations.some(item => item.status === "archived") && (
                              <details className="story-bible-archive-list" open={showArchivedLocations} onToggle={event => setShowArchivedLocations(event.currentTarget.open)}>
                                <summary>Archived locations · {storyboard.locations.filter(item => item.status === "archived").length}</summary>
                                {storyboard.locations.filter(item => item.status === "archived").map(location => {
                                  const edit = locationEditDraft(location);
                                  return (
                                    <article className="storyboard-asset archived" key={location.id}>
                                      <div className="storyboard-asset-heading"><strong>{location.name}</strong><span>{location.environment_type} · ARCHIVED</span></div>
                                      {location.time_period && <small>{location.time_period}</small>}
                                      {location.description && <p>{location.description}</p>}
                                      {location.visual_notes && <small>Visual: {location.visual_notes}</small>}
                                      {canEditStoryboard && (
                                        <details className="story-bible-edit">
                                          <summary>Edit archived profile</summary>
                                          <form className="storyboard-mini-form" onSubmit={event => { event.preventDefault(); saveLocationDetails(location); }}>
                                            <label>Name<input required maxLength={160} value={edit.name} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, name: event.target.value } }))} /></label>
                                            <label>Environment<select value={edit.environment_type} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, environment_type: event.target.value } }))}>
                                              <option value="interior">Interior</option><option value="exterior">Exterior</option><option value="vehicle">Vehicle</option><option value="virtual">Virtual / imagined</option><option value="unspecified">Unspecified</option>
                                            </select></label>
                                            <label>Time period<input maxLength={120} value={edit.time_period} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, time_period: event.target.value } }))} /></label>
                                            <label>Description<textarea rows={3} maxLength={10000} value={edit.description} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, description: event.target.value } }))} /></label>
                                            <label>Visual notes<textarea rows={3} maxLength={10000} value={edit.visual_notes} onChange={event => setLocationEdits(current => ({ ...current, [location.id]: { ...edit, visual_notes: event.target.value } }))} /></label>
                                            <button className="secondary-button" type="submit" disabled={loading || !edit.name.trim()}>Save profile</button>
                                          </form>
                                        </details>
                                      )}
                                      {canEditStoryboard && <button type="button" className="secondary-button" disabled={loading} onClick={() => updateLocationStatus(location, "active")}>Restore location</button>}
                                    </article>
                                  );
                                })}
                              </details>
                            )}
                          </div>
                        </section>
                      </div>

                      {canEditStoryboard && (
                        <form className="storyboard-scene-form" onSubmit={submitScene}>
                          <div className="section-kicker">ADD TO THE STORYBOARD</div><h3>Create a scene</h3>
                          {selectedProject.format === "tv_series" && <label>Episode<select required value={sceneEpisodeId} onChange={event => setSceneEpisodeId(event.target.value)}>
                            <option value="">Select an active episode</option>
                            {storyboard.seasons.filter(season => season.status === "active").flatMap(season => season.episodes.filter(episode => episode.status === "active").map(episode => <option key={episode.id} value={episode.id}>S{season.season_number} · E{episode.episode_number} — {episode.title}</option>))}
                          </select><small className="field-hint">Create a season and episode above before adding scenes to a series.</small></label>}
                          <label>Scene title<input required maxLength={160} value={sceneTitle} onChange={event => setSceneTitle(event.target.value)} placeholder="INT. APARTMENT — NIGHT" /></label>
                          <label>Summary<textarea rows={3} maxLength={10000} value={sceneSummary} onChange={event => setSceneSummary(event.target.value)} placeholder="What happens in this scene?" /></label>
                          <label>Requirements<textarea rows={2} maxLength={10000} value={sceneRequirements} onChange={event => setSceneRequirements(event.target.value)} placeholder="Props, visual effects, stunts, special conditions, continuity…" /></label>
                          <div className="storyboard-scene-form-row">
                            <label>Estimated duration (seconds)<input type="number" min="1" max="86400" value={sceneDuration} onChange={event => setSceneDuration(event.target.value)} placeholder="e.g. 90" /></label>
                            <label>Primary location<select value={sceneLocationId} onChange={event => setSceneLocationId(event.target.value)}><option value="">No location assigned</option>{storyboard.locations.filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                          </div>
                          <label>Characters in this scene <select multiple size={Math.min(5, Math.max(2, storyboard.characters.filter(item => item.status === "active").length))} value={sceneCharacterIds} onChange={event => setSceneCharacterIds(Array.from(event.target.selectedOptions, option => option.value))}>{storyboard.characters.filter(item => item.status === "active").map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><small className="field-hint">Use Ctrl / Cmd to select more than one character.</small></label>
                          <div className="form-actions"><span>New scenes are added to the end of the sequence.</span><button className="primary-button" type="submit" disabled={loading || !sceneTitle.trim() || (selectedProject.format === "tv_series" && !sceneEpisodeId)}><Plus size={15} /> Add scene</button></div>
                        </form>
                      )}

                      <div className="storyboard-scene-list">
                        <div className="section-kicker">{selectedProject.format === "tv_series" ? "EPISODE SCENES" : "SCENE SEQUENCE"} · {storyboard.scenes.length} SCENES</div>
                        {storyboard.scenes.length === 0 && <p className="muted-note">Add the first scene to begin breaking down the approved narrative.</p>}
                        {[...storyboard.scenes].sort((a, b) =>
                          (a.season_number || 0) - (b.season_number || 0) ||
                          (a.episode_number || 0) - (b.episode_number || 0) ||
                          a.scene_order - b.scene_order
                        ).map(scene => {
                          const latestScript = scene.script_versions[scene.script_versions.length - 1] || null;
                          const siblingScenes = storyboard.scenes.filter(item => item.episode_id === scene.episode_id).sort((a, b) => a.scene_order - b.scene_order);
                          const siblingIndex = siblingScenes.findIndex(item => item.id === scene.id);
                          const edit = sceneEditDraft(scene);
                          return (
                            <article className="storyboard-scene-card" key={scene.id}>
                              <div className="storyboard-scene-heading">
                                <div className="scene-number">{scene.scene_order.toString().padStart(2, "0")}</div>
                                <div className="storyboard-scene-title"><div className="section-kicker">SCENE {scene.scene_order}</div><h3>{scene.title}</h3><span>{scene.episode_id ? `S${scene.season_number} · E${scene.episode_number} — ${scene.episode_title} · ` : ""}{scene.estimated_duration_seconds ? `Estimated ${scene.estimated_duration_seconds}s` : "Duration not estimated"}{scene.location_name ? ` · ${scene.location_name}${storyboard.locations.find(item => item.id === scene.location_id)?.status === "archived" ? " (archived)" : ""}` : ""}</span></div>
                                {canEditStoryboard && <div className="scene-order-actions"><button type="button" className="quiet-button" disabled={loading || siblingIndex === 0} onClick={() => moveScene(scene, -1)} aria-label="Move scene up">↑</button><button type="button" className="quiet-button" disabled={loading || siblingIndex === siblingScenes.length - 1} onClick={() => moveScene(scene, 1)} aria-label="Move scene down">↓</button></div>}
                              </div>
                              {scene.summary && <p className="storyboard-scene-summary">{scene.summary}</p>}
                              {scene.requirements && <div className="scene-requirements"><strong>Requirements</strong><p>{scene.requirements}</p></div>}
                              <div className="scene-participants"><strong>Characters</strong>{scene.characters.length ? scene.characters.map(character => {
                                const archived = storyboard.characters.find(item => item.id === character.id)?.status === "archived";
                                return <span key={character.id}>{character.name}{archived ? " · archived" : ""}</span>;
                              }) : <small>None assigned</small>}</div>

                              {canEditStoryboard && (
                                <details className="scene-edit-panel">
                                  <summary>Edit scene details</summary>
                                  <form className="storyboard-mini-form" onSubmit={event => { event.preventDefault(); saveSceneDetails(scene); }}>
                                    {selectedProject.format === "tv_series" && <label>Episode<select required value={edit.episode_id} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, episode_id: event.target.value } }))}>
                                      {storyboard.seasons.flatMap(season => season.episodes.filter(episode => (season.status === "active" && episode.status === "active") || episode.id === scene.episode_id).map(episode => <option key={episode.id} value={episode.id}>S{season.season_number} · E{episode.episode_number} — {episode.title}</option>))}
                                    </select></label>}
                                    <label>Scene title<input required maxLength={160} value={edit.title} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, title: event.target.value } }))} /></label>
                                    <label>Summary<textarea rows={3} maxLength={10000} value={edit.summary} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, summary: event.target.value } }))} /></label>
                                    <label>Production requirements<textarea rows={2} maxLength={10000} value={edit.requirements} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, requirements: event.target.value } }))} /></label>
                                    <div className="storyboard-scene-form-row">
                                      <label>Estimated duration (seconds)<input type="number" min="1" max="86400" value={edit.estimated_duration_seconds} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, estimated_duration_seconds: event.target.value } }))} /></label>
                                      <label>Primary location<select value={edit.location_id} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, location_id: event.target.value } }))}><option value="">No location assigned</option>{storyboard.locations.filter(item => item.status === "active" || item.id === edit.location_id).map(item => <option key={item.id} value={item.id}>{item.name}{item.status === "archived" ? " · ARCHIVED (existing reference)" : ""}</option>)}</select></label>
                                    </div>
                                    <label>Characters in this scene<select multiple size={Math.min(5, Math.max(2, storyboard.characters.filter(item => item.status === "active").length))} value={edit.character_ids} onChange={event => setSceneEdits(current => ({ ...current, [scene.id]: { ...edit, character_ids: Array.from(event.target.selectedOptions, option => option.value) } }))}>{storyboard.characters.filter(item => item.status === "active" || edit.character_ids.includes(item.id)).map(item => <option key={item.id} value={item.id}>{item.name}{item.status === "archived" ? " · ARCHIVED (existing participant)" : ""}</option>)}</select></label>
                                    <button className="secondary-button" type="submit" disabled={loading || !edit.title.trim()}>Save scene details</button>
                                  </form>
                                </details>
                              )}

                              <div className="scene-passage-area">
                                <div className="section-kicker">LINKED STORY PASSAGES · {scene.passages.length}</div>
                                {scene.passages.map(passage => <details className="scene-passage" key={passage.id}><summary>Passage {passage.reference_order} · source characters {passage.start_offset}–{passage.end_offset}</summary><pre>{passage.passage_snapshot}</pre></details>)}
                                {canEditStoryboard && <div className="scene-passage-form"><label>Paste an exact excerpt from the approved narrative<textarea rows={3} maxLength={10000} value={passageDrafts[scene.id] || ""} onChange={event => setPassageDrafts(current => ({ ...current, [scene.id]: event.target.value }))} placeholder="Copy the exact passage from the approved narrative above…" /></label><label>Occurrence when the same passage appears more than once<input type="number" min="1" max="100" value={passageOccurrences[scene.id] || "1"} onChange={event => setPassageOccurrences(current => ({ ...current, [scene.id]: event.target.value }))} /></label><button type="button" className="secondary-button" disabled={loading || !(passageDrafts[scene.id] || "").trim()} onClick={() => addScenePassage(scene)}>Link exact passage</button></div>}
                              </div>

                              <div className="scene-script-area">
                                <div className="section-kicker">WORKING SCREENPLAY · {scene.script_versions.length} REVISIONS</div>
                                {latestScript && (
                                  <details className="scene-current-script">
                                    <summary>Current script · Revision {latestScript.revision_number}</summary>
                                    <pre>{latestScript.content}</pre>
                                  </details>
                                )}
                                {canEditStoryboard && (
                                  <>
                                    {!scriptEditorOpen[scene.id] && (
                                      <button type="button" className="secondary-button" onClick={() => startStructuredScriptEdit(scene)}>
                                        {latestScript ? "Edit as structured screenplay" : "Write screenplay"}
                                      </button>
                                    )}
                                    {scriptEditorOpen[scene.id] && (
                                      <div className="structured-script-editor">
                                        <div className="script-editor-intro">
                                          <strong>{latestScript ? `Create revision ${latestScript.revision_number + 1}` : "Create first screenplay revision"}</strong>
                                          <span>Each block is stored separately and remains in order. Dialogue is attributed to a story character, not a performer.</span>
                                        </div>
                                        {(scriptElementDrafts[scene.id] || []).map((element, elementIndex) => (
                                          <div className="script-element-card" key={elementIndex}>
                                            <div className="script-element-heading">
                                              <span>{(elementIndex + 1).toString().padStart(2, "0")}</span>
                                              <select
                                                aria-label="Screenplay block type"
                                                value={element.element_type}
                                                onChange={event => {
                                                  const elementType = event.target.value as ScriptElementType;
                                                  updateScriptElement(scene.id, elementIndex, {
                                                    element_type: elementType,
                                                    character_id: elementType === "dialogue" || elementType === "parenthetical" ? element.character_id : "",
                                                  });
                                                }}
                                              >
                                                <option value="action">Action</option>
                                                <option value="dialogue">Dialogue</option>
                                                <option value="parenthetical">Parenthetical</option>
                                                <option value="transition">Transition</option>
                                                <option value="production_note">Production note</option>
                                              </select>
                                              <button type="button" className="quiet-button" disabled={elementIndex === 0} onClick={() => moveScriptElement(scene.id, elementIndex, -1)} aria-label="Move screenplay block up">↑</button>
                                              <button type="button" className="quiet-button" disabled={elementIndex === (scriptElementDrafts[scene.id] || []).length - 1} onClick={() => moveScriptElement(scene.id, elementIndex, 1)} aria-label="Move screenplay block down">↓</button>
                                              <button type="button" className="quiet-button danger-button" onClick={() => removeScriptElement(scene.id, elementIndex)} aria-label="Remove screenplay block">Remove</button>
                                            </div>
                                            {(element.element_type === "dialogue" || element.element_type === "parenthetical") && (
                                              <label className="script-speaker-select">
                                                {element.element_type === "dialogue" ? "Speaking character" : "Associated character (optional)"}
                                                <select
                                                  required={element.element_type === "dialogue"}
                                                  value={element.character_id}
                                                  onChange={event => updateScriptElement(scene.id, elementIndex, { character_id: event.target.value })}
                                                >
                                                  <option value="">Select a character</option>
                                                  {scene.characters.filter(character =>
                                                    storyboard.characters.some(item => item.id === character.id && item.status === "active")
                                                  ).map(character => (
                                                    <option key={character.id} value={character.id}>{character.name}</option>
                                                  ))}
                                                </select>
                                              </label>
                                            )}
                                            <label className="script-element-content">
                                              {element.element_type === "action" ? "Action / description"
                                                : element.element_type === "dialogue" ? "Spoken line"
                                                : element.element_type === "parenthetical" ? "Delivery / parenthetical"
                                                : element.element_type === "transition" ? "Transition"
                                                : "Production note"}
                                              <textarea
                                                rows={element.element_type === "action" ? 4 : 2}
                                                maxLength={50000}
                                                value={element.content}
                                                onChange={event => updateScriptElement(scene.id, elementIndex, { content: event.target.value })}
                                                placeholder={element.element_type === "action" ? "Describe what happens on screen…"
                                                  : element.element_type === "dialogue" ? "Write the character's spoken words…"
                                                  : element.element_type === "parenthetical" ? "e.g. quietly, after a pause…"
                                                  : element.element_type === "transition" ? "e.g. CUT TO:"
                                                  : "Camera, sound, continuity, or production instruction…"}
                                              />
                                            </label>
                                          </div>
                                        ))}
                                        <div className="script-add-blocks">
                                          <span>Add a block</span>
                                          <button type="button" onClick={() => addScriptElement(scene.id, "action")}>+ Action</button>
                                          <button type="button" onClick={() => addScriptElement(scene.id, "dialogue")}>+ Dialogue</button>
                                          <button type="button" onClick={() => addScriptElement(scene.id, "parenthetical")}>+ Parenthetical</button>
                                          <button type="button" onClick={() => addScriptElement(scene.id, "transition")}>+ Transition</button>
                                          <button type="button" onClick={() => addScriptElement(scene.id, "production_note")}>+ Production note</button>
                                        </div>
                                        <div className="script-editor-actions">
                                          <span>{(scriptElementDrafts[scene.id] || []).length} ordered blocks · Save creates a new immutable revision</span>
                                          <button type="button" className="quiet-button" onClick={() => cancelStructuredScriptEdit(scene.id)}>Discard changes</button>
                                          <button type="button" className="primary-button" disabled={loading || !(scriptElementDrafts[scene.id] || []).length || (scriptElementDrafts[scene.id] || []).some(item => !item.content.trim() || (item.element_type === "dialogue" && !item.character_id))} onClick={() => saveSceneScript(scene)}>{latestScript ? "Save new revision" : "Save screenplay"}</button>
                                        </div>
                                      </div>
                                    )}
                                  </>
                                )}
                                {scene.script_versions.length > 0 && (
                                  <details className="scene-script-history">
                                    <summary>Script history</summary>
                                    {[...scene.script_versions].reverse().map(version => (
                                      <article key={version.id}>
                                        <strong>Revision {version.revision_number} · {version.author_display_name}</strong>
                                        {version.elements.length > 0 ? (
                                          <div className="script-history-elements">
                                            {version.elements.map(element => (
                                              <div className={`script-history-element ${element.element_type}`} key={element.id}>
                                                <small>{element.element_order.toString().padStart(2, "0")} · {element.element_type.replace("_", " ")}{element.character_name ? ` · ${element.character_name}` : ""}</small>
                                                <p>{element.content}</p>
                                              </div>
                                            ))}
                                          </div>
                                        ) : <pre>{version.content}</pre>}
                                      </article>
                                    ))}
                                  </details>
                                )}
                              </div>
                            </article>
                          );
                        })}
                      </div>
                    </>
                  )}
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
