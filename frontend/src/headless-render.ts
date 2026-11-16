import * as THREE from "three";

type Vec3 = [number, number, number];
type RenderEvent = {
  timestamp_ms: number;
  event_type: string;
  cast_member_instance_id: string | null;
  payload: Record<string, unknown>;
};
type RenderClip = {
  clip_id: string;
  scene_title: string;
  timeline_start_ms: number;
  source_in_ms: number;
  source_out_ms: number;
  duration_ms: number;
  transition: string;
  title_overlay: string;
  camera_snapshot: Record<string, unknown>;
  cast_members: Array<{
    id: string;
    actor_name_snapshot: string;
    character_name_snapshot: string;
    role_label_snapshot: string;
  }>;
  events: RenderEvent[];
};
type RenderManifest = {
  width: number;
  height: number;
  fps: number;
  duration_ms: number;
  clips: RenderClip[];
};
type CharacterRig = {
  root: THREE.Group;
  basePosition: THREE.Vector3;
  baseRotation: THREE.Euler;
  baseScale: THREE.Vector3;
};
type SceneBundle = {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  rigs: Map<string, CharacterRig>;
  controlsTarget: THREE.Vector3;
};
type RendererWindow = Window & {
  storyforgeRenderFrame?: (manifest: RenderManifest, timelineMs: number) => void;
};

const cameraPositions: Record<string, Vec3> = {
  wide: [8, 7, 11],
  close: [4, 3, 6],
  overhead: [0, 15, 0.1],
  reverse: [-8, 6, -10],
};

const outputCanvas = document.querySelector<HTMLCanvasElement>("#frame")!;
const status = document.querySelector<HTMLDivElement>("#status")!;
const context = outputCanvas.getContext("2d")!;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(0x161c18);
const bundles = new Map<string, SceneBundle>();
let currentClipId = "";

function vector(value: unknown): THREE.Vector3 | null {
  if (Array.isArray(value) && value.length >= 3) {
    const values = value.slice(0, 3).map(Number);
    return values.every(Number.isFinite) ? new THREE.Vector3(values[0], values[1], values[2]) : null;
  }
  if (value && typeof value === "object") {
    const candidate = value as Record<string, unknown>;
    const values = [candidate.x, candidate.y, candidate.z].map(Number);
    return values.every(Number.isFinite) ? new THREE.Vector3(values[0], values[1], values[2]) : null;
  }
  return null;
}

function transformPayload(event: RenderEvent): Record<string, unknown> {
  const nested = event.payload.transform;
  return nested && typeof nested === "object" ? nested as Record<string, unknown> : event.payload;
}

function makeLabel(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 96;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "rgba(20,25,21,.88)";
  ctx.beginPath();
  ctx.roundRect(8, 8, 496, 80, 16);
  ctx.fill();
  ctx.fillStyle = "#e8eddd";
  ctx.font = "bold 34px Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text.slice(0, 28), 256, 48);
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false }));
  sprite.scale.set(2.8, 0.52, 1);
  return sprite;
}

function makeCharacter(index: number, total: number, name: string): CharacterRig {
  const root = new THREE.Group();
  const hue = (index * 0.19 + 0.08) % 1;
  const cloth = new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(hue, 0.32, 0.48), roughness: 0.82 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xb58c70, roughness: 0.9 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x292e2a, roughness: 0.95 });
  const add = (geometry: THREE.BufferGeometry, material: THREE.Material, position: Vec3) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...position);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    root.add(mesh);
    return mesh;
  };
  add(new THREE.CylinderGeometry(0.31, 0.4, 0.95, 12), cloth, [0, 1.35, 0]);
  add(new THREE.SphereGeometry(0.28, 16, 12), skin, [0, 2.02, 0]);
  add(new THREE.CylinderGeometry(0.12, 0.13, 0.72, 10), skin, [-0.43, 1.35, 0]).rotation.z = -0.24;
  add(new THREE.CylinderGeometry(0.12, 0.13, 0.72, 10), skin, [0.43, 1.35, 0]).rotation.z = 0.24;
  add(new THREE.CylinderGeometry(0.14, 0.16, 0.82, 10), dark, [-0.17, 0.45, 0]).rotation.z = -0.04;
  add(new THREE.CylinderGeometry(0.14, 0.16, 0.82, 10), dark, [0.17, 0.45, 0]).rotation.z = 0.04;
  const label = makeLabel(name);
  label.position.set(0, 2.65, 0);
  root.add(label);
  const spacing = Math.max(2.2, Math.min(3.8, 10 / Math.max(1, total)));
  root.position.set((index - (total - 1) / 2) * spacing, 0, 0);
  return { root, basePosition: root.position.clone(), baseRotation: root.rotation.clone(), baseScale: root.scale.clone() };
}

function createBundle(clip: RenderClip, width: number, height: number): SceneBundle {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x161c18);
  scene.fog = new THREE.Fog(0x161c18, 18, 48);
  const camera = new THREE.PerspectiveCamera(44, width / height, 0.1, 100);
  const initial = clip.camera_snapshot || {};
  const initialPosition = vector(initial.position);
  const initialPreset = typeof initial.preset === "string" ? initial.preset : "wide";
  camera.position.copy(initialPosition || new THREE.Vector3(...(cameraPositions[initialPreset] || cameraPositions.wide)));
  const target = vector(initial.target) || new THREE.Vector3(0, 1, 0);

  scene.add(new THREE.HemisphereLight(0xdde8d6, 0x343c32, 2.1));
  const key = new THREE.DirectionalLight(0xffe6c1, 3.1);
  key.position.set(-5, 10, 6);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  scene.add(key);
  const fill = new THREE.PointLight(0x8ea7bd, 32, 22);
  fill.position.set(6, 5, -4);
  scene.add(fill);

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(36, 36), new THREE.MeshStandardMaterial({ color: 0x353c34, roughness: 0.95 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);
  const grid = new THREE.GridHelper(36, 36, 0x64715e, 0x414b40);
  grid.position.y = 0.012;
  scene.add(grid);
  const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x596052, roughness: 0.9 });
  const wall = new THREE.Mesh(new THREE.BoxGeometry(18, 5, 0.28), wallMaterial);
  wall.position.set(0, 2.5, -7);
  scene.add(wall);
  const sideWall = new THREE.Mesh(new THREE.BoxGeometry(0.28, 5, 14), wallMaterial);
  sideWall.position.set(-9, 2.5, 0);
  scene.add(sideWall);
  const platform = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.8, 0.3, 32), new THREE.MeshStandardMaterial({ color: 0x89916e, metalness: 0.25, roughness: 0.55 }));
  platform.position.set(5, 0.16, -3);
  scene.add(platform);
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(3.5, 0.8, 2.2), new THREE.MeshStandardMaterial({ color: 0x665747, roughness: 0.8 }));
  plinth.position.set(-4, 0.4, -2);
  scene.add(plinth);

  const rigs = new Map<string, CharacterRig>();
  clip.cast_members.forEach((member, index) => {
    const rig = makeCharacter(index, clip.cast_members.length, member.character_name_snapshot || member.actor_name_snapshot || "Cast");
    scene.add(rig.root);
    rigs.set(member.id, rig);
  });
  return { scene, camera, rigs, controlsTarget: target };
}

function getBundle(clip: RenderClip, width: number, height: number): SceneBundle {
  if (!bundles.has(clip.clip_id)) bundles.set(clip.clip_id, createBundle(clip, width, height));
  return bundles.get(clip.clip_id)!;
}

function applyClip(bundle: SceneBundle, clip: RenderClip, sourceMs: number): void {
  const cameraEvents = clip.events.filter(event => event.event_type === "camera" && event.timestamp_ms <= sourceMs);
  const latestCamera = cameraEvents[cameraEvents.length - 1];
  const cameraPayload = latestCamera?.payload || clip.camera_snapshot || {};
  const cameraPosition = vector(cameraPayload.position);
  const preset = typeof cameraPayload.preset === "string" ? cameraPayload.preset : "wide";
  bundle.camera.position.copy(cameraPosition || new THREE.Vector3(...(cameraPositions[preset] || cameraPositions.wide)));
  bundle.controlsTarget.copy(vector(cameraPayload.target) || new THREE.Vector3(0, 1, 0));
  bundle.camera.lookAt(bundle.controlsTarget);

  for (const [memberId, rig] of bundle.rigs.entries()) {
    const samples = clip.events.filter(event => event.event_type === "transform" && event.cast_member_instance_id === memberId);
    let previousIndex = -1;
    for (let index = 0; index < samples.length; index += 1) {
      if (samples[index].timestamp_ms <= sourceMs) previousIndex = index;
      else break;
    }
    const previous = previousIndex >= 0 ? samples[previousIndex] : null;
    const next = samples[previousIndex + 1] || null;
    const startTime = previous?.timestamp_ms ?? 0;
    const endTime = next?.timestamp_ms ?? startTime;
    const amount = endTime > startTime ? THREE.MathUtils.clamp((sourceMs - startTime) / (endTime - startTime), 0, 1) : 1;
    const startPayload = previous ? transformPayload(previous) : {};
    const endPayload = next ? transformPayload(next) : {};
    const position = vector(startPayload.position) || rig.basePosition;
    const nextPosition = vector(endPayload.position);
    rig.root.position.copy(nextPosition ? position.clone().lerp(nextPosition, amount) : position);
    const rotation = vector(startPayload.rotation) || new THREE.Vector3(rig.baseRotation.x, rig.baseRotation.y, rig.baseRotation.z);
    const nextRotation = vector(endPayload.rotation);
    const resolvedRotation = nextRotation ? rotation.clone().lerp(nextRotation, amount) : rotation;
    rig.root.rotation.set(resolvedRotation.x, resolvedRotation.y, resolvedRotation.z);
    const scale = vector(startPayload.scale) || rig.baseScale;
    const nextScale = vector(endPayload.scale);
    rig.root.scale.copy(nextScale ? scale.clone().lerp(nextScale, amount) : scale);
  }
}

function renderFrame(manifest: RenderManifest, timelineMs: number): void {
  const clips = manifest.clips;
  if (!clips.length) throw new Error("The render manifest contains no clips.");
  const time = Math.max(0, Math.min(manifest.duration_ms, timelineMs));
  let clip = clips[clips.length - 1];
  for (const candidate of clips) {
    if (time < candidate.timeline_start_ms + candidate.duration_ms) {
      clip = candidate;
      break;
    }
  }
  const elapsed = Math.max(0, Math.min(clip.duration_ms, time - clip.timeline_start_ms));
  const sourceMs = clip.source_in_ms + elapsed;
  const bundle = getBundle(clip, manifest.width, manifest.height);
  if (currentClipId !== clip.clip_id) currentClipId = clip.clip_id;
  applyClip(bundle, clip, sourceMs);
  renderer.render(bundle.scene, bundle.camera);

  outputCanvas.width = manifest.width;
  outputCanvas.height = manifest.height;
  context.clearRect(0, 0, manifest.width, manifest.height);
  context.drawImage(renderer.domElement, 0, 0, manifest.width, manifest.height);

  const fadeMs = Math.min(450, Math.floor(clip.duration_ms / 3));
  let fadeOpacity = 0;
  if (fadeMs > 0) {
    if (clip.transition !== "cut") fadeOpacity = Math.max(fadeOpacity, 1 - elapsed / fadeMs);
    const nextClip = clips[clips.indexOf(clip) + 1];
    if (nextClip && nextClip.transition !== "cut") fadeOpacity = Math.max(fadeOpacity, 1 - (clip.duration_ms - elapsed) / fadeMs);
  }
  if (fadeOpacity > 0) {
    context.fillStyle = `rgba(0,0,0,${THREE.MathUtils.clamp(fadeOpacity, 0, 1)})`;
    context.fillRect(0, 0, manifest.width, manifest.height);
  }
  const title = clip.title_overlay || "";
  if (title.trim()) {
    const boxWidth = Math.min(manifest.width - 100, 1100);
    const boxHeight = 104;
    const x = (manifest.width - boxWidth) / 2;
    const y = manifest.height - 180;
    context.fillStyle = "rgba(8,12,9,.78)";
    context.beginPath();
    context.roundRect(x, y, boxWidth, boxHeight, 18);
    context.fill();
    context.fillStyle = "#f0f1e7";
    context.font = "600 42px Arial";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(title.slice(0, 80), manifest.width / 2, y + boxHeight / 2, boxWidth - 40);
  }
}

renderer.setSize(1280, 720, false);
document.body.appendChild(renderer.domElement);
renderer.domElement.style.display = "none";
status.textContent = "Headless renderer ready";
(window as RendererWindow).storyforgeRenderFrame = renderFrame;
