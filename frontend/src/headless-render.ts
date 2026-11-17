import {
  createProductionStage, disposeProductionStage, loadProductionAssets, renderProductionClip,
  type ProductionStage, type SceneClip,
} from "./productionScene";

type RenderManifest = {
  renderer: string; width: number; height: number; fps: number;
  clips: SceneClip[];
};
type RendererApi = {
  initialize: (manifest: RenderManifest) => Promise<{ frame_count: number }>;
  renderFrame: (frameIndex: number) => void;
  dispose: () => void;
};
declare global { interface Window { storyForgeRenderer?: RendererApi } }

const canvas = document.getElementById("frame") as HTMLCanvasElement;
const context = canvas.getContext("2d", { alpha: false });
if (!context) throw new Error("2D frame compositor is unavailable.");

let stage: ProductionStage | null = null;
let clips: SceneClip[] = [];
let starts: number[] = [];
let fps = 24;
let frameCount = 0;
let width = 1280;
let height = 720;
const outgoingBuffer = document.createElement("canvas");
const incomingBuffer = document.createElement("canvas");
const outgoingContext = outgoingBuffer.getContext("2d");
const incomingContext = incomingBuffer.getContext("2d");

function drawClip(clipIndex: number, localMs: number, target: CanvasRenderingContext2D): void {
  if (!stage) throw new Error("Renderer has not been initialized.");
  const rendered = renderProductionClip(stage, clips[clipIndex], localMs);
  target.drawImage(rendered, 0, 0, width, height);
}

function renderFrame(frameIndex: number): void {
  if (!stage || !context || !outgoingContext || !incomingContext) throw new Error("Renderer is not ready.");
  if (!Number.isInteger(frameIndex) || frameIndex < 0 || frameIndex >= frameCount) {
    throw new Error("Requested frame is outside the render manifest.");
  }
  const timelineMs = frameIndex * 1000 / fps;
  for (let index = 1; index < clips.length; index += 1) {
    const overlap = Number((clips[index] as SceneClip & { transition_duration_ms?: number }).transition_duration_ms || 0);
    const transitionStart = starts[index];
    if (overlap <= 0 || timelineMs < transitionStart || timelineMs >= transitionStart + overlap) continue;
    const progress = Math.max(0, Math.min(1, (timelineMs - transitionStart) / overlap));
    const previousLocal = Math.max(0, timelineMs - starts[index - 1]);
    const nextLocal = Math.max(0, timelineMs - transitionStart);
    outgoingContext.clearRect(0, 0, width, height);
    incomingContext.clearRect(0, 0, width, height);
    drawClip(index - 1, previousLocal, outgoingContext);
    drawClip(index, nextLocal, incomingContext);
    context.clearRect(0, 0, width, height);
    const transition = (clips[index] as SceneClip & { transition?: string }).transition;
    if (transition === "fade") {
      if (progress < .5) {
        context.globalAlpha = 1; context.drawImage(outgoingBuffer, 0, 0);
        context.globalAlpha = progress * 2;
        context.fillStyle = "#000"; context.fillRect(0, 0, width, height);
      } else {
        context.globalAlpha = 1; context.fillStyle = "#000"; context.fillRect(0, 0, width, height);
        context.globalAlpha = (progress - .5) * 2;
        context.drawImage(incomingBuffer, 0, 0);
      }
    } else {
      context.globalAlpha = 1; context.drawImage(outgoingBuffer, 0, 0);
      context.globalAlpha = progress; context.drawImage(incomingBuffer, 0, 0);
    }
    context.globalAlpha = 1;
    return;
  }

  let active = 0;
  for (let index = 0; index < starts.length; index += 1) {
    if (starts[index] <= timelineMs) active = index;
    else break;
  }
  context.clearRect(0, 0, width, height);
  drawClip(active, Math.max(0, timelineMs - starts[active]), context);
}

window.storyForgeRenderer = {
  async initialize(manifest) {
    if (manifest.renderer !== "storyforge-headless-3d-v1") throw new Error("Unsupported 3D renderer manifest.");
    if (!Array.isArray(manifest.clips) || manifest.clips.length === 0) throw new Error("Render manifest contains no clips.");
    width = Number(manifest.width); height = Number(manifest.height); fps = Number(manifest.fps);
    if (width < 320 || width > 1920 || height < 180 || height > 1080 || ![12, 24, 30].includes(fps)) {
      throw new Error("Unsupported render dimensions or frame rate.");
    }
    canvas.width = width; canvas.height = height;
    outgoingBuffer.width = width; outgoingBuffer.height = height;
    incomingBuffer.width = width; incomingBuffer.height = height;
    clips = manifest.clips;
    starts = [0];
    for (let index = 1; index < clips.length; index += 1) {
      const overlap = Number((clips[index] as SceneClip & { transition_duration_ms?: number }).transition_duration_ms || 0);
      starts.push(starts[index - 1] + clips[index - 1].duration_ms - overlap);
    }
    const duration = starts[starts.length - 1] + clips[clips.length - 1].duration_ms;
    frameCount = Math.ceil(duration * fps / 1000);
    if (frameCount < 1 || frameCount > 14400) throw new Error("Render exceeds the ten-minute frame budget.");
    stage = createProductionStage(width, height);
    await loadProductionAssets(stage, clips);
    return { frame_count: frameCount };
  },
  renderFrame,
  dispose() {
    if (stage) disposeProductionStage(stage);
    stage = null; clips = []; starts = []; frameCount = 0;
  },
};
