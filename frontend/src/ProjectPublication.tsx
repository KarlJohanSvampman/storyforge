import { useEffect, useState } from "react";

type VideoAsset = { id: string; title: string; duration_ms: number; width: number; height: number; status: string };
type Release = { id: string; release_number: number; slug: string; title: string; synopsis: string; visibility: string; published_at: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body as T;
}

export default function ProjectPublication({ projectId, storyboardId, canPublish }: { projectId: string; storyboardId: string; canPublish: boolean }) {
  const [videos, setVideos] = useState<VideoAsset[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [masterId, setMasterId] = useState("");
  const [trailerId, setTrailerId] = useState("");
  const [title, setTitle] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [videoRows, releaseRows] = await Promise.all([
      request<VideoAsset[]>(`/api/projects/${projectId}/production/videos`),
      request<Release[]>(`/api/projects/${projectId}/releases`),
    ]);
    const active = videoRows.filter(video => video.status === "active");
    setVideos(active);
    setReleases(releaseRows);
    setMasterId(current => active.some(video => video.id === current) ? current : active[0]?.id || "");
  }
  useEffect(() => { refresh().catch(reason => setError(reason.message)); }, [projectId]);

  async function publish(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      await request(`/api/projects/${projectId}/releases`, {
        method: "POST",
        body: JSON.stringify({
          video_asset_id: masterId, storyboard_id: storyboardId,
          trailer_video_asset_id: trailerId || null,
          title: title.trim() || null, synopsis: synopsis.trim() || null,
        }),
      });
      setTitle(""); setSynopsis(""); setTrailerId("");
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not publish release."); }
    finally { setBusy(false); }
  }

  return <section style={{ margin: "30px 0", padding: 22, border: "1px solid #34343b", borderRadius: 12, background: "#151519" }}>
    <div className="section-kicker">PUBLICATION</div>
    <h2 style={{ margin: "8px 0" }}>Release editions</h2>
    <p className="muted-note">Publishing creates a permanent snapshot and automatically generates a 16:9 cover from the master video (or a designed title cover if no frame can be extracted).</p>
    {canPublish && <form onSubmit={publish} style={{ display: "grid", gap: 12, maxWidth: 720, marginTop: 18 }}>
      <label>Finished master<select required value={masterId} onChange={event => setMasterId(event.target.value)}><option value="">Choose a finished video</option>{videos.map(video => <option key={video.id} value={video.id}>{video.title} · {Math.round(video.duration_ms / 1000)}s</option>)}</select></label>
      <label>Trailer (optional)<select value={trailerId} onChange={event => setTrailerId(event.target.value)}><option value="">No separate trailer</option>{videos.filter(video => video.id !== masterId).map(video => <option key={video.id} value={video.id}>{video.title} · {Math.round(video.duration_ms / 1000)}s</option>)}</select></label>
      <label>Release title<input maxLength={240} value={title} onChange={event => setTitle(event.target.value)} placeholder="Defaults to the project title" /></label>
      <label>Synopsis<textarea rows={3} maxLength={20000} value={synopsis} onChange={event => setSynopsis(event.target.value)} placeholder="A short public description" /></label>
      <button className="primary-button" disabled={busy || !masterId}>{busy ? "Publishing…" : "Publish immutable release"}</button>
    </form>}
    {error && <p role="alert" style={{ color: "#e49a8e" }}>{error}</p>}
    <div style={{ marginTop: 24, display: "grid", gap: 10 }}>
      {releases.map(release => <article key={release.id} style={{ padding: 14, border: "1px solid #303037", borderRadius: 8 }}>
        <strong>Release {release.release_number} · {release.title}</strong>
        <p className="muted-note">{release.visibility} · {new Date(release.published_at).toLocaleString()}</p>
        {release.visibility === "private" ? <small>Private — visible to project members only.</small> : <a href={`/releases/${release.slug}`} target="_blank" rel="noreferrer">Open permanent release page ↗</a>}
      </article>)}
      {releases.length === 0 && <p className="muted-note">No releases published yet.</p>}
    </div>
  </section>;
}
