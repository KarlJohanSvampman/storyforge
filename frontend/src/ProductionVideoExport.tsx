import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Download, Film, LoaderCircle, Video } from "lucide-react";
import ThreeSceneViewport from "./ThreeSceneViewport";

type SceneOption = { id: string; title: string };
type EditItem = {
  id: string; take_id: string; scene_id: string; item_order: number;
  in_ms: number; out_ms: number; transition: string; title_overlay: string;
};
type ReplayEvent = {
  id: string; timestamp_ms: number; event_type: string;
  cast_member_instance_id: string | null; payload: Record<string, unknown>;
};
type ReplayCastMember = {
  id: string; actor_name_snapshot: string; character_name_snapshot: string; role_label_snapshot: string;
};
type ReplayData = {
  take_id: string; duration_ms: number; events: ReplayEvent[];
  cast_members: ReplayCastMember[]; camera_snapshot: Record<string, unknown>;
};
type AudioRenderJob = {
  id: string; status: string; duration_ms: number | null; download_url: string | null;
  sequence_revision: number; output_size_bytes: number | null;
};
type Props = {
  projectId: string; sequenceId: string; sequenceName: string;
  sequenceRevision: number; items: EditItem[]; scenes: SceneOption[];
};

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function nextFrame(): Promise<void> {
  return new Promise(resolve => requestAnimationFrame(() => resolve()));
}

function safeName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "storyforge-sequence";
}

export default function ProductionVideoExport({
  projectId, sequenceId, sequenceName, sequenceRevision, items, scenes,
}: Props) {
  const [replays, setReplays] = useState<Record<string, ReplayData>>({});
  const [audioJobs, setAudioJobs] = useState<AudioRenderJob[]>([]);
  const [audioJobId, setAudioJobId] = useState("");
  const [activeItemIndex, setActiveItemIndex] = useState(0);
  const [clipElapsedMs, setClipElapsedMs] = useState(0);
  const [loading, setLoading] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [renderedUrl, setRenderedUrl] = useState("");
  const [renderedSize, setRenderedSize] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cancelRef = useRef(false);

  const orderedItems = useMemo(() => [...items].sort((a, b) => a.item_order - b.item_order), [items]);
  const totalDurationMs = orderedItems.reduce((sum, item) => sum + item.out_ms - item.in_ms, 0);
  const activeItem = orderedItems[activeItemIndex];
  const activeReplay = activeItem ? replays[activeItem.id] : undefined;
  const sceneTitle = activeItem ? scenes.find(scene => scene.id === activeItem.scene_id)?.title || "Scene" : "Sequence";
  const activeAudioJobs = audioJobs.filter(job => job.status === "completed" && job.download_url);
  const selectedAudioJob = activeAudioJobs.find(job => job.id === audioJobId) || null;

  const onCanvasReady = useCallback((canvas: HTMLCanvasElement | null) => {
    canvasRef.current = canvas;
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    setReplays({});
    Promise.all(orderedItems.map(async item => {
      const replay = await api<ReplayData>(`/api/projects/${projectId}/takes/${item.take_id}/replay`);
      return [item.id, replay] as const;
    })).then(rows => {
      if (alive) setReplays(Object.fromEntries(rows));
    }).catch(err => {
      if (alive) setError(err instanceof Error ? err.message : "Could not load selected take replays.");
    }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [projectId, sequenceId, orderedItems]);

  useEffect(() => {
    let alive = true;
    const refreshAudioJobs = () => {
      api<AudioRenderJob[]>(`/api/projects/${projectId}/edit-sequences/${sequenceId}/audio-renders`)
        .then(jobs => {
          if (!alive) return;
          setAudioJobs(jobs);
          const latest = jobs.find(job => job.status === "completed" && job.download_url);
          setAudioJobId(current => current && jobs.some(job => job.id === current && job.status === "completed")
            ? current : latest?.id || "");
        })
        .catch(() => { /* video-only rendering remains available */ });
    };
    refreshAudioJobs();
    const timer = window.setInterval(refreshAudioJobs, 3000);
    return () => { alive = false; window.clearInterval(timer); };
  }, [projectId, sequenceId]);

  useEffect(() => () => {
    if (renderedUrl) URL.revokeObjectURL(renderedUrl);
  }, [renderedUrl]);

  const transitionOpacity = (() => {
    if (!activeItem) return 0;
    const duration = activeItem.out_ms - activeItem.in_ms;
    const fadeMs = Math.min(450, Math.floor(duration / 3));
    if (fadeMs <= 0) return 0;
    const fadeIn = activeItem.transition !== "cut" && activeItemIndex > 0
      ? Math.max(0, 1 - clipElapsedMs / fadeMs) : 0;
    const nextItem = orderedItems[activeItemIndex + 1];
    const fadeOut = nextItem && nextItem.transition !== "cut"
      ? Math.max(0, 1 - (duration - clipElapsedMs) / fadeMs) : 0;
    return Math.max(fadeIn, fadeOut);
  })();

  async function renderSequence() {
    if (!canvasRef.current || orderedItems.length === 0 || loading || rendering) return;
    const missing = orderedItems.find(item => !replays[item.id]);
    if (missing) {
      setError("One or more selected takes could not be loaded for rendering.");
      return;
    }
    const canvas = canvasRef.current;
    if (typeof canvas.captureStream !== "function" || typeof MediaRecorder === "undefined") {
      setError("This browser does not support canvas video capture and MediaRecorder.");
      return;
    }
    const mimeType = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm",
    ].find(type => MediaRecorder.isTypeSupported(type));
    if (!mimeType) {
      setError("No supported WebM recording format is available in this browser.");
      return;
    }

    setRendering(true);
    setProgress(0);
    setError("");
    setRenderedSize(0);
    cancelRef.current = false;
    let audioContext: AudioContext | null = null;
    let audioSource: AudioBufferSourceNode | null = null;
    let videoStream: MediaStream | null = null;
    let combinedStream: MediaStream | null = null;
    let recorder: MediaRecorder | null = null;
    let blobUrl = "";

    try {
      setActiveItemIndex(0);
      setClipElapsedMs(0);
      await nextFrame();
      await nextFrame();

      videoStream = canvas.captureStream(30);
      const streamTracks = [...videoStream.getVideoTracks()];
      if (selectedAudioJob?.download_url) {
        const response = await fetch(selectedAudioJob.download_url, { credentials: "same-origin" });
        if (!response.ok) throw new Error("The selected WAV master could not be downloaded.");
        const audioBytes = await response.arrayBuffer();
        audioContext = new AudioContext();
        await audioContext.resume();
        const audioBuffer = await audioContext.decodeAudioData(audioBytes);
        const destination = audioContext.createMediaStreamDestination();
        audioSource = audioContext.createBufferSource();
        audioSource.buffer = audioBuffer;
        audioSource.connect(destination);
        streamTracks.push(...destination.stream.getAudioTracks());
      }
      combinedStream = new MediaStream(streamTracks);
      recorder = new MediaRecorder(combinedStream, {
        mimeType, videoBitsPerSecond: 8_000_000, audioBitsPerSecond: 192_000,
      });
      const chunks: BlobPart[] = [];
      const completed = new Promise<Blob>((resolve, reject) => {
        recorder!.ondataavailable = event => { if (event.data.size > 0) chunks.push(event.data); };
        recorder!.onerror = () => reject(new Error("The browser video recorder failed."));
        recorder!.onstop = () => resolve(new Blob(chunks, { type: mimeType }));
      });
      recorder.start(500);
      if (audioSource && audioContext) {
        audioSource.start(audioContext.currentTime + 0.05, 0, Math.min(audioSource.buffer!.duration, totalDurationMs / 1000));
      }
      await new Promise(resolve => window.setTimeout(resolve, 50));

      let completedTimelineMs = 0;
      for (let index = 0; index < orderedItems.length; index += 1) {
        if (cancelRef.current) throw new Error("Video export was cancelled.");
        const item = orderedItems[index];
        const replay = replays[item.id];
        const clipDuration = item.out_ms - item.in_ms;
        setActiveItemIndex(index);
        setClipElapsedMs(0);
        await nextFrame();
        await nextFrame();
        const clipStart = performance.now();
        let lastUpdate = clipStart;
        while (true) {
          if (cancelRef.current) throw new Error("Video export was cancelled.");
          const now = performance.now();
          const elapsed = Math.min(clipDuration, now - clipStart);
          if (now - lastUpdate >= 30 || elapsed >= clipDuration) {
            setClipElapsedMs(elapsed);
            setProgress(Math.min(99, Math.round((completedTimelineMs + elapsed) / totalDurationMs * 100)));
            lastUpdate = now;
          }
          if (elapsed >= clipDuration) break;
          await nextFrame();
        }
        completedTimelineMs += clipDuration;
        setProgress(Math.min(99, Math.round(completedTimelineMs / totalDurationMs * 100)));
        if (index + 1 < orderedItems.length) {
          setActiveItemIndex(index + 1);
          setClipElapsedMs(0);
          await nextFrame();
        }
        void replay;
      }
      await new Promise(resolve => window.setTimeout(resolve, 150));
      if (recorder.state !== "inactive") recorder.stop();
      const blob = await completed;
      if (!blob.size) throw new Error("The browser produced an empty video file.");
      blobUrl = URL.createObjectURL(blob);
      setRenderedUrl(previous => {
        if (previous) URL.revokeObjectURL(previous);
        return blobUrl;
      });
      setRenderedSize(blob.size);
      setProgress(100);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${safeName(sequenceName)}-r${sequenceRevision}.webm`;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      if (recorder && recorder.state !== "inactive") recorder.stop();
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      setError(err instanceof Error ? err.message : "Video export failed.");
    } finally {
      audioSource?.stop();
      await audioContext?.close().catch(() => undefined);
      combinedStream?.getTracks().forEach(track => track.stop());
      videoStream?.getTracks().forEach(track => track.stop());
      setRendering(false);
    }
  }

  function cancelRender() {
    cancelRef.current = true;
  }

  return <section className="production-video-export">
    <div className="audio-timeline-heading">
      <div><div className="section-kicker">M4 · VIDEO EXPORT</div><h4>Sequence render</h4></div>
      <Film size={18} />
    </div>
    <p className="muted-note">Renders the selected takes in sequence order from the Three.js scene viewport. A completed WAV master can be muxed into the WebM recording.</p>
    {error && <p className="production-error">{error}</p>}
    {loading && <p className="muted-note">Loading replay data for {orderedItems.length} clips…</p>}
    {!loading && orderedItems.length > 0 && <div className="video-export-preview">
      <ThreeSceneViewport
        castMembers={activeReplay?.cast_members || []}
        sceneTitle={sceneTitle}
        cameraPreset="wide"
        replayEvents={activeReplay?.events || []}
        playheadMs={(activeItem?.in_ms || 0) + clipElapsedMs}
        titleOverlay={activeItem?.title_overlay || ""}
        fadeOpacity={transitionOpacity}
        onCanvasReady={onCanvasReady}
      />
      <div className="video-export-clip-strip">
        {orderedItems.map((item, index) => <span className={index === activeItemIndex ? "active" : ""} key={item.id}>
          {index + 1}. {scenes.find(scene => scene.id === item.scene_id)?.title || "Scene"} · {item.out_ms - item.in_ms} ms
        </span>)}
      </div>
    </div>}
    {activeAudioJobs.length > 0 && <label className="video-audio-select">Audio master
      <select value={audioJobId} onChange={event => setAudioJobId(event.target.value)}>
        <option value="">No audio</option>
        {activeAudioJobs.map(job => <option key={job.id} value={job.id}>Revision {job.sequence_revision} · {job.duration_ms || 0} ms</option>)}
      </select>
    </label>}
    <div className="video-export-actions">
      <button type="button" className="primary-button" disabled={loading || rendering || orderedItems.length === 0 || Object.keys(replays).length !== orderedItems.length} onClick={() => void renderSequence()}>
        {rendering ? <LoaderCircle size={14} className="spin" /> : <Video size={14} />}
        {rendering ? `Rendering ${progress}%` : "Render and download WebM"}
      </button>
      {rendering && <button type="button" className="quiet-button" onClick={cancelRender}>Cancel</button>}
      {renderedUrl && !rendering && <a className="secondary-button" href={renderedUrl} download={`${safeName(sequenceName)}-r${sequenceRevision}.webm`}><Download size={13} /> Download last render</a>}
      {renderedSize > 0 && <small>{(renderedSize / 1024 / 1024).toFixed(1)} MiB · WebM</small>}
    </div>
    {rendering && <div className="video-render-progress"><span style={{ width: progress + "%" }} /></div>}
    <p className="muted-note">This is a real-time browser capture. Cuts and title overlays are included; fade/dissolve transitions are approximated as fade-through-black. The current procedural scene models do not yet provide skeletal animation or deterministic physics replay.</p>
  </section>;
}
