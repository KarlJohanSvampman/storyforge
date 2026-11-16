import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AudioLines, Download, Pause, Play, Plus, Upload, Volume2, VolumeX } from "lucide-react";

type AudioAsset = {
  id: string; title: string; original_filename: string; content_type: string;
  size_bytes: number; duration_ms: number | null; download_url: string;
};
type AudioClip = {
  id: string; track_id: string; media_asset_id: string; asset_title: string;
  original_filename: string; content_type: string; download_url: string;
  asset_duration_ms: number | null; clip_order: number; source_in_ms: number;
  source_out_ms: number; timeline_start_ms: number; gain: number;
  fade_in_ms: number; fade_out_ms: number;
};
type AudioTrack = {
  id: string; name: string; role: "dialogue" | "music" | "effects" | "ambience" | "voiceover";
  track_order: number; gain: number; pan: number; muted: boolean; solo: boolean; clips: AudioClip[];
};
type AudioRenderJob = { id: string; status: "queued" | "running" | "completed" | "failed"; sequence_revision: number; duration_ms: number | null; output_size_bytes: number | null; output_sha256: string | null; error_message: string; download_url: string | null; created_at: string; completed_at: string | null };
type Props = { projectId: string; sequenceId: string; editable: boolean; videoDurationMs: number };

const roles: AudioTrack["role"][] = ["dialogue", "music", "effects", "ambience", "voiceover"];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: init?.body instanceof FormData
      ? { ...(init?.headers || {}) }
      : { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Audio request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const root = (projectId: string) => `/api/projects/${projectId}`;

async function readAudioDuration(file: File): Promise<number | null> {
  return new Promise(resolve => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    const finish = (duration: number | null) => {
      audio.removeAttribute("src");
      URL.revokeObjectURL(url);
      resolve(duration);
    };
    audio.addEventListener("loadedmetadata", () => {
      finish(Number.isFinite(audio.duration) && audio.duration > 0 ? Math.round(audio.duration * 1000) : null);
    }, { once: true });
    audio.addEventListener("error", () => finish(null), { once: true });
    audio.src = url;
  });
}

export default function AudioTimeline({ projectId, sequenceId, editable, videoDurationMs }: Props) {
  const [assets, setAssets] = useState<AudioAsset[]>([]);
  const [tracks, setTracks] = useState<AudioTrack[]>([]);
  const [renderJobs, setRenderJobs] = useState<AudioRenderJob[]>([]);
  const [assetTitle, setAssetTitle] = useState("");
  const [assetDuration, setAssetDuration] = useState("");
  const [trackName, setTrackName] = useState("Music");
  const [trackRole, setTrackRole] = useState<AudioTrack["role"]>("music");
  const [clipDrafts, setClipDrafts] = useState<Record<string, { assetId: string; sourceIn: string; sourceOut: string; timelineStart: string; fadeIn: string; fadeOut: string }>>({});
  const [playheadMs, setPlayheadMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const buffersRef = useRef<Map<string, AudioBuffer>>(new Map());
  const frameRef = useRef<number | null>(null);
  const playbackStartRef = useRef<{ contextTime: number; playheadMs: number } | null>(null);

  const audioDurationMs = useMemo(() => Math.max(0, ...tracks.flatMap(track =>
    track.clips.map(clip => clip.timeline_start_ms + clip.source_out_ms - clip.source_in_ms),
  )), [tracks]);
  const durationMs = Math.max(videoDurationMs, audioDurationMs);

  async function refresh() {
    const [assetRows, trackRows, jobRows] = await Promise.all([
      request<AudioAsset[]>(`${root(projectId)}/production/media`),
      request<AudioTrack[]>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-tracks`),
      request<AudioRenderJob[]>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-renders`),
    ]);
    setAssets(assetRows);
    setTracks(trackRows);
    setRenderJobs(jobRows);
  }

  useEffect(() => {
    let alive = true;
    stopSources();
    setIsPlaying(false);
    setPlayheadMs(0);
    setAssets([]);
    setTracks([]);
    setRenderJobs([]);
    Promise.all([
      request<AudioAsset[]>(`${root(projectId)}/production/media`),
      request<AudioTrack[]>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-tracks`),
      request<AudioRenderJob[]>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-renders`),
    ]).then(([assetRows, trackRows, jobRows]) => {
      if (alive) { setAssets(assetRows); setTracks(trackRows); setRenderJobs(jobRows); }
    }).catch(err => { if (alive) setError(err instanceof Error ? err.message : "Could not load audio timeline."); });
    return () => { alive = false; };
  }, [projectId, sequenceId]);

  const hasActiveRender = renderJobs.some(job => job.status === "queued" || job.status === "running");
  useEffect(() => {
    if (!hasActiveRender) return;
    const timer = window.setInterval(() => {
      request<AudioRenderJob[]>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-renders`)
        .then(setRenderJobs)
        .catch(err => setError(err instanceof Error ? err.message : "Could not refresh audio render status."));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [projectId, sequenceId, hasActiveRender]);

  function stopSources() {
    sourcesRef.current.forEach(source => { try { source.stop(); } catch { /* already stopped */ } });
    sourcesRef.current = [];
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    playbackStartRef.current = null;
  }

  function stopPlayback() {
    const context = audioContextRef.current;
    const start = playbackStartRef.current;
    if (context && start) {
      setPlayheadMs(Math.max(0, Math.min(durationMs, start.playheadMs + (context.currentTime - start.contextTime) * 1000)));
    }
    stopSources();
    setIsPlaying(false);
  }

  useEffect(() => () => {
    stopSources();
    audioContextRef.current?.close();
  }, []);

  async function uploadAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("audio-file") as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file || !assetTitle.trim()) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const data = new FormData();
      data.append("file", file);
      data.append("title", assetTitle.trim());
      const measuredDuration = Number(assetDuration) > 0
        ? Math.round(Number(assetDuration))
        : await readAudioDuration(file);
      if (measuredDuration && measuredDuration > 0) data.append("duration_ms", String(measuredDuration));
      await request<AudioAsset>(`${root(projectId)}/production/media`, { method: "POST", body: data });
      await refresh();
      setAssetTitle(""); setAssetDuration(""); form.reset();
      setNotice("Audio asset uploaded and stored in the project media library.");
    } catch (err) { setError(err instanceof Error ? err.message : "Audio upload failed."); }
    finally { setBusy(false); }
  }

  async function createTrack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trackName.trim()) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await request<AudioTrack>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-tracks`, {
        method: "POST", body: JSON.stringify({ name: trackName, role: trackRole }),
      });
      await refresh();
      setTrackName(roles.includes(trackRole) ? (trackRole === "music" ? "Music" : trackRole[0].toUpperCase() + trackRole.slice(1)) : "Track");
      setNotice("Audio track created.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create audio track."); }
    finally { setBusy(false); }
  }

  function draftFor(track: AudioTrack) {
    return clipDrafts[track.id] || {
      assetId: assets[0]?.id || "", sourceIn: "0",
      sourceOut: String(assets[0]?.duration_ms || 30000),
      timelineStart: "0", fadeIn: "0", fadeOut: "0",
    };
  }

  async function addClip(event: FormEvent<HTMLFormElement>, track: AudioTrack) {
    event.preventDefault();
    const draft = draftFor(track);
    if (!draft.assetId) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await request<AudioTrack>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-tracks/${track.id}/clips`, {
        method: "POST",
        body: JSON.stringify({
          media_asset_id: draft.assetId, source_in_ms: Number(draft.sourceIn),
          source_out_ms: Number(draft.sourceOut), timeline_start_ms: Number(draft.timelineStart),
          fade_in_ms: Number(draft.fadeIn), fade_out_ms: Number(draft.fadeOut),
        }),
      });
      await refresh();
      setNotice("Audio clip placed on the timeline.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not add audio clip."); }
    finally { setBusy(false); }
  }

  async function updateTrack(track: AudioTrack, patch: Partial<AudioTrack>) {
    setBusy(true); setError(""); setNotice("");
    try {
      await request<AudioTrack>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-tracks/${track.id}`, {
        method: "PATCH", body: JSON.stringify(patch),
      });
      await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update audio track."); }
    finally { setBusy(false); }
  }

  async function removeClip(track: AudioTrack, clip: AudioClip) {
    setBusy(true); setError(""); setNotice("");
    try {
      await request<AudioTrack>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-tracks/${track.id}/clips/${clip.id}`, { method: "DELETE" });
      await refresh();
      setNotice("Audio clip removed from the timeline.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not remove audio clip."); }
    finally { setBusy(false); }
  }

  async function createRender() {
    setBusy(true); setError(""); setNotice("");
    try {
      const job = await request<AudioRenderJob>(`${root(projectId)}/edit-sequences/${sequenceId}/audio-renders`, { method: "POST" });
      setRenderJobs(rows => [job, ...rows.filter(row => row.id !== job.id)]);
      setNotice("Offline audio render queued. The renderer will process it in the background.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not queue audio render."); }
    finally { setBusy(false); }
  }

  async function loadBuffer(clip: AudioClip): Promise<AudioBuffer> {
    const cached = buffersRef.current.get(clip.media_asset_id);
    if (cached) return cached;
    const response = await fetch(clip.download_url, { credentials: "same-origin" });
    if (!response.ok) throw new Error(`Could not load ${clip.asset_title} (${response.status}).`);
    const bytes = await response.arrayBuffer();
    const context = audioContextRef.current || new AudioContext();
    audioContextRef.current = context;
    const buffer = await context.decodeAudioData(bytes);
    buffersRef.current.set(clip.media_asset_id, buffer);
    return buffer;
  }

  async function startPlayback() {
    if (isPlaying || durationMs <= 0) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const context = audioContextRef.current || new AudioContext();
      audioContextRef.current = context;
      await context.resume();
      const hasSolo = tracks.some(track => track.solo);
      const startTime = context.currentTime + 0.05;
      const activeSources: AudioBufferSourceNode[] = [];
      const pending = tracks.flatMap(track => {
        if (track.muted || (hasSolo && !track.solo)) return [];
        return track.clips.map(clip => ({ track, clip }));
      });
      const buffers = await Promise.all(pending.map(({ clip }) => loadBuffer(clip)));
      pending.forEach(({ track, clip }, index) => {
        const buffer = buffers[index];
        const clipDuration = clip.source_out_ms - clip.source_in_ms;
        const elapsed = Math.max(0, playheadMs - clip.timeline_start_ms);
        if (elapsed >= clipDuration) return;
        const delay = Math.max(0, clip.timeline_start_ms - playheadMs) / 1000;
        const sourceOffset = clip.source_in_ms / 1000 + elapsed / 1000;
        if (sourceOffset >= buffer.duration) return;
        const remaining = Math.min(clipDuration / 1000 - elapsed / 1000, buffer.duration - sourceOffset);
        if (remaining <= 0) return;
        const source = context.createBufferSource();
        source.buffer = buffer;
        const gain = context.createGain();
        const pan = context.createStereoPanner();
        const initialFade = clip.fade_in_ms > elapsed ? Math.max(0, elapsed / Math.max(1, clip.fade_in_ms)) : 1;
        gain.gain.setValueAtTime(track.gain * clip.gain * initialFade, startTime + delay);
        if (clip.fade_in_ms > elapsed) {
          gain.gain.linearRampToValueAtTime(track.gain * clip.gain, startTime + delay + (clip.fade_in_ms - elapsed) / 1000);
        }
        if (clip.fade_out_ms > 0) {
          const fadeOutStart = clipDuration - clip.fade_out_ms;
          const fadeRemaining = Math.max(0, clipDuration - elapsed);
          if (elapsed >= fadeOutStart) {
            const fadeLevel = Math.max(0, fadeRemaining / clip.fade_out_ms);
            gain.gain.setValueAtTime(track.gain * clip.gain * fadeLevel, startTime + delay);
            gain.gain.linearRampToValueAtTime(0, startTime + delay + fadeRemaining / 1000);
          } else {
            const untilFade = (fadeOutStart - elapsed) / 1000;
            gain.gain.setValueAtTime(track.gain * clip.gain, startTime + delay + untilFade);
            gain.gain.linearRampToValueAtTime(0, startTime + delay + fadeRemaining / 1000);
          }
        }
        pan.pan.setValueAtTime(track.pan, startTime + delay);
        source.connect(gain);
        gain.connect(pan);
        pan.connect(context.destination);
        source.start(startTime + delay, sourceOffset, remaining);
        activeSources.push(source);
      });
      sourcesRef.current = activeSources;
      playbackStartRef.current = { contextTime: startTime, playheadMs };
      setIsPlaying(true);
      const tick = () => {
        const start = playbackStartRef.current;
        if (!start || !audioContextRef.current) return;
        const next = Math.max(0, Math.min(durationMs, start.playheadMs + (audioContextRef.current.currentTime - start.contextTime) * 1000));
        setPlayheadMs(next);
        if (next >= durationMs) { stopSources(); setIsPlaying(false); return; }
        frameRef.current = requestAnimationFrame(tick);
      };
      frameRef.current = requestAnimationFrame(tick);
    } catch (err) {
      stopSources();
      setError(err instanceof Error ? err.message : "Audio preview failed.");
    } finally { setBusy(false); }
  }

  function seek(value: number) {
    if (isPlaying) stopPlayback();
    setPlayheadMs(value);
  }

  return <section className="audio-timeline">
    <div className="audio-timeline-heading">
      <div><div className="section-kicker">M3.2 · MEDIA & SOUND</div><h4>Audio timeline</h4></div>
      <AudioLines size={18} />
    </div>
    {error && <p className="production-error">{error}</p>}
    {notice && <p className="production-notice">{notice}</p>}
    {editable && <div className="audio-library-grid">
      <form onSubmit={uploadAsset} className="audio-form">
        <strong>Project audio library</strong>
        <label>Asset title<input value={assetTitle} onChange={event => setAssetTitle(event.target.value)} placeholder="Dialogue edit, score, ambience…" /></label>
        <label>Duration (ms, optional)<input type="number" min="1" value={assetDuration} onChange={event => setAssetDuration(event.target.value)} placeholder="Read from audio if known" /></label>
        <label>Audio file<input name="audio-file" type="file" accept=".mp3,.wav,.m4a,.ogg,.aac,.flac,audio/*" required /></label>
        <button className="secondary-button" disabled={busy || !assetTitle.trim()}><Upload size={13} /> Upload audio</button>
      </form>
      <form onSubmit={createTrack} className="audio-form">
        <strong>Create mix track</strong>
        <label>Track name<input value={trackName} onChange={event => setTrackName(event.target.value)} /></label>
        <label>Track role<select value={trackRole} onChange={event => setTrackRole(event.target.value as AudioTrack["role"])}>{roles.map(role => <option key={role} value={role}>{role}</option>)}</select></label>
        <button className="secondary-button" disabled={busy || !trackName.trim()}><Plus size={13} /> Add track</button>
      </form>
    </div>}
    <div className="audio-asset-strip">
      <strong>{assets.length} audio assets</strong>
      {assets.map(asset => <span key={asset.id}>{asset.title} · {asset.duration_ms ? `${asset.duration_ms} ms` : "duration unknown"}</span>)}
      {assets.length === 0 && <small>Upload MP3, WAV, M4A, OGG, AAC or FLAC source media to begin.</small>}
    </div>
    <div className="audio-preview-controls">
      <button type="button" className="secondary-button" disabled={busy || durationMs <= 0} onClick={() => isPlaying ? stopPlayback() : void startPlayback()}>
        {isPlaying ? <Pause size={13} /> : <Play size={13} />}{isPlaying ? "Pause mix" : "Preview mix"}
      </button>
      <strong>{Math.round(playheadMs)} / {durationMs} ms</strong>
      <input aria-label="Audio mix playhead" type="range" min="0" max={Math.max(1, durationMs)} value={Math.min(playheadMs, durationMs)} onChange={event => seek(Number(event.target.value))} />
    </div>
    <div className="audio-render-panel">
      <div><strong>Offline master render</strong><small>Render the current immutable mix snapshot to a 48 kHz stereo WAV.</small></div>
      {editable && <button type="button" className="secondary-button" disabled={busy || tracks.every(track => track.muted || track.clips.length === 0)} onClick={() => void createRender()}><AudioLines size={13} /> Render mastered WAV</button>}
      {renderJobs.length > 0 && <div className="audio-render-jobs">
        {renderJobs.map(job => <div className="audio-render-job" key={job.id}>
          <span className={"render-status " + job.status}>{job.status}</span>
          <small>Revision {job.sequence_revision} · {job.duration_ms ? job.duration_ms + " ms" : "duration pending"}</small>
          {job.status === "completed" && job.download_url && <a className="secondary-button" href={job.download_url}><Download size={12} /> Download WAV</a>}
          {job.status === "failed" && <small className="production-error">{job.error_message}</small>}
        </div>)}
      </div>}
    </div>
    <div className="audio-track-list">
      {tracks.map(track => <article className="audio-track" key={track.id}>
        <div className="audio-track-header">
          <div><strong>{track.track_order.toString().padStart(2, "0")} · {track.name}</strong><small>{track.role} · {track.clips.length} clips</small></div>
          {editable && <div className="audio-track-actions">
            <label>Gain <input type="range" min="0" max="2" step="0.05" value={track.gain} disabled={busy} onChange={event => setTracks(rows => rows.map(row => row.id === track.id ? { ...row, gain: Number(event.target.value) } : row))} onMouseUp={event => updateTrack(track, { gain: Number((event.target as HTMLInputElement).value) })} onTouchEnd={event => updateTrack(track, { gain: Number((event.target as HTMLInputElement).value) })} /></label>
            <label>Pan <input type="range" min="-1" max="1" step="0.05" value={track.pan} disabled={busy} onChange={event => setTracks(rows => rows.map(row => row.id === track.id ? { ...row, pan: Number(event.target.value) } : row))} onMouseUp={event => updateTrack(track, { pan: Number((event.target as HTMLInputElement).value) })} onTouchEnd={event => updateTrack(track, { pan: Number((event.target as HTMLInputElement).value) })} /></label>
            <button type="button" className={track.muted ? "audio-toggle active" : "audio-toggle"} title="Mute track" onClick={() => updateTrack(track, { muted: !track.muted })}><VolumeX size={13} /></button>
            <button type="button" className={track.solo ? "audio-toggle active" : "audio-toggle"} title="Solo track" onClick={() => updateTrack(track, { solo: !track.solo })}><Volume2 size={13} /></button>
          </div>}
        </div>
        <div className="audio-clip-list">
          {track.clips.map(clip => <div className="audio-clip-row" key={clip.id}>
            <span>{clip.asset_title}</span><small>Source {clip.source_in_ms}–{clip.source_out_ms} ms</small>
            <small>Timeline {clip.timeline_start_ms}–{clip.timeline_start_ms + clip.source_out_ms - clip.source_in_ms} ms</small>
            <small>Fades {clip.fade_in_ms}/{clip.fade_out_ms} ms</small>
            {editable && <button type="button" className="quiet-button" disabled={busy} onClick={() => removeClip(track, clip)}>Remove</button>}
          </div>)}
          {track.clips.length === 0 && <small className="muted-note">No clips on this track yet.</small>}
        </div>
        {editable && assets.length > 0 && <form className="audio-clip-form" onSubmit={event => addClip(event, track)}>
          <label>Source<select value={draftFor(track).assetId} onChange={event => {
            const asset = assets.find(row => row.id === event.target.value);
            setClipDrafts(rows => ({ ...rows, [track.id]: { ...draftFor(track), assetId: event.target.value, sourceOut: String(asset?.duration_ms || 30000) } }));
          }}>{assets.map(asset => <option key={asset.id} value={asset.id}>{asset.title}</option>)}</select></label>
          <label>In ms<input type="number" min="0" value={draftFor(track).sourceIn} onChange={event => setClipDrafts(rows => ({ ...rows, [track.id]: { ...draftFor(track), sourceIn: event.target.value } }))} /></label>
          <label>Out ms<input type="number" min="1" value={draftFor(track).sourceOut} onChange={event => setClipDrafts(rows => ({ ...rows, [track.id]: { ...draftFor(track), sourceOut: event.target.value } }))} /></label>
          <label>Timeline start<input type="number" min="0" value={draftFor(track).timelineStart} onChange={event => setClipDrafts(rows => ({ ...rows, [track.id]: { ...draftFor(track), timelineStart: event.target.value } }))} /></label>
          <label>Fade in<input type="number" min="0" value={draftFor(track).fadeIn} onChange={event => setClipDrafts(rows => ({ ...rows, [track.id]: { ...draftFor(track), fadeIn: event.target.value } }))} /></label>
          <label>Fade out<input type="number" min="0" value={draftFor(track).fadeOut} onChange={event => setClipDrafts(rows => ({ ...rows, [track.id]: { ...draftFor(track), fadeOut: event.target.value } }))} /></label>
          <button className="secondary-button" disabled={busy}><Plus size={12} /> Place clip</button>
        </form>}
      </article>)}
      {tracks.length === 0 && <p className="muted-note">Create a dialogue, music, effects, ambience or voiceover track.</p>}
    </div>
    <p className="muted-note">Mix preview schedules source audio against the sequence millisecond clock, applying track gain, pan, mute/solo and clip fades. It is a browser preview; final mastered audio rendering is not yet available.</p>
  </section>;
}
