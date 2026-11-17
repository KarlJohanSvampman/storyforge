import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

export type SceneCastMember = {
  id: string;
  character_name?: string;
  actor_name?: string;
  character_name_snapshot?: string;
  actor_name_snapshot?: string;
  character_id?: string;
};
export type SceneReplayEvent = {
  timestamp_ms: number;
  event_type: string;
  cast_member_instance_id: string | null;
  payload: Record<string, unknown>;
};
export type SceneClip = {
  scene_title?: string;
  in_ms: number;
  duration_ms: number;
  title_overlay?: string;
  camera_snapshot?: Record<string, unknown>;
  cast_members?: SceneCastMember[];
  events?: SceneReplayEvent[];
  location_id?: string | null;
  production_assets?: SceneProductionAsset[];
};

export type SceneProductionAsset = {
  asset_id: string;
  target_type: "character" | "location";
  target_id: string;
  version: number;
  sha256: string;
  file_format: "glb" | "gltf";
  render_url: string;
  download_url?: string;
  transform: { position?: number[]; rotation?: number[]; scale?: number[] };
};
export type ProductionStage = {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  rigs: Map<string, THREE.Group>;
  titleSprite: THREE.Sprite;
  sceneLabel: THREE.Sprite;
  fadePlane: THREE.Mesh;
  assetObjects: Map<string, THREE.Object3D>;
  width: number;
  height: number;
};

const CAMERA_POSITIONS: Record<string, [number, number, number]> = {
  wide: [8, 7, 11], close: [4, 3, 6], overhead: [0, 15, 0.1], reverse: [-8, 6, -10],
};

function labelSprite(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512; canvas.height = 96;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = "rgba(20,25,21,.86)";
    context.beginPath(); context.roundRect(8, 8, 496, 80, 16); context.fill();
    context.fillStyle = "#e8eddd"; context.font = "bold 34px Arial";
    context.textAlign = "center"; context.textBaseline = "middle";
    context.fillText(text.slice(0, 28), 256, 48);
  }
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false,
  }));
  sprite.scale.set(2.8, .52, 1);
  return sprite;
}

function titleSprite(): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 1200; canvas.height = 220;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas), transparent: true, depthTest: false, depthWrite: false,
  }));
  sprite.scale.set(6.2, 1.14, 1);
  sprite.position.set(0, -1.2, -4.4);
  sprite.renderOrder = 1000;
  sprite.userData.canvas = canvas;
  return sprite;
}


function sceneLabelSprite(): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 900;
  canvas.height = 100;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas), transparent: true, depthTest: false, depthWrite: false,
  }));
  sprite.scale.set(5.2, .58, 1);
  sprite.position.set(0, 2.75, -4.4);
  sprite.renderOrder = 999;
  sprite.userData.canvas = canvas;
  return sprite;
}

function updateSceneLabel(sprite: THREE.Sprite, text: string): void {
  const canvas = sprite.userData.canvas as HTMLCanvasElement;
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(8,12,9,.72)";
  context.beginPath();
  context.roundRect(18, 14, 864, 72, 18);
  context.fill();
  context.fillStyle = "#dce5d7";
  context.font = "600 34px Arial";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text.slice(0, 70), 450, 50);
  sprite.visible = Boolean(text.trim());
  (sprite.material as THREE.SpriteMaterial).map!.needsUpdate = true;
}

function updateTitle(sprite: THREE.Sprite, text: string): void {
  const canvas = sprite.userData.canvas as HTMLCanvasElement;
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  if (text.trim()) {
    context.fillStyle = "rgba(8,12,9,.78)";
    context.beginPath(); context.roundRect(28, 28, 1144, 164, 22); context.fill();
    context.fillStyle = "#f0f1e7"; context.font = "600 58px Arial";
    context.textAlign = "center"; context.textBaseline = "middle";
    context.fillText(text.slice(0, 54), 600, 110);
  }
  sprite.visible = Boolean(text.trim());
  (sprite.material as THREE.SpriteMaterial).map!.needsUpdate = true;
}

export function createCharacterRig(index: number, total: number, label: string): THREE.Group {
  const group = new THREE.Group();
  const hue = (index * .19 + .08) % 1;
  const cloth = new THREE.MeshStandardMaterial({
    color: new THREE.Color().setHSL(hue, .32, .48), roughness: .82,
  });
  const skin = new THREE.MeshStandardMaterial({ color: 0xb58c70, roughness: .9 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x292e2a, roughness: .95 });
  const add = (geometry: THREE.BufferGeometry, material: THREE.Material, position: [number, number, number]) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...position); mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.userData.isProceduralCharacterPart = true;
    group.add(mesh); return mesh;
  };
  add(new THREE.CylinderGeometry(.31, .4, .95, 12), cloth, [0, 1.35, 0]);
  add(new THREE.SphereGeometry(.28, 16, 12), skin, [0, 2.02, 0]);
  add(new THREE.CylinderGeometry(.12, .13, .72, 10), skin, [-.43, 1.35, 0]).rotation.z = -.24;
  add(new THREE.CylinderGeometry(.12, .13, .72, 10), skin, [.43, 1.35, 0]).rotation.z = .24;
  add(new THREE.CylinderGeometry(.14, .16, .82, 10), dark, [-.17, .45, 0]).rotation.z = -.04;
  add(new THREE.CylinderGeometry(.14, .16, .82, 10), dark, [.17, .45, 0]).rotation.z = .04;
  const tag = labelSprite(label);
  tag.position.set(0, 2.65, 0); group.add(tag);
  const spacing = Math.max(2.2, Math.min(3.8, 10 / Math.max(1, total)));
  group.position.set((index - (total - 1) / 2) * spacing, 0, 0);
  group.userData.basePosition = group.position.clone();
  group.userData.baseRotation = group.rotation.clone();
  group.userData.baseScale = group.scale.clone();
  return group;
}

function addBox(scene: THREE.Scene, size: [number, number, number], position: [number, number, number],
                color: number, castShadow = true): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size),
    new THREE.MeshStandardMaterial({ color, roughness: .86 }));
  mesh.position.set(...position); mesh.castShadow = castShadow; mesh.receiveShadow = true;
  scene.add(mesh); return mesh;
}

export function createProductionStage(width: number, height: number): ProductionStage {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x161c18);
  scene.fog = new THREE.Fog(0x161c18, 18, 48);
  const camera = new THREE.PerspectiveCamera(44, width / height, .1, 100);
  camera.position.set(...CAMERA_POSITIONS.wide);
  scene.add(camera);
  const title = titleSprite(); camera.add(title);
  const sceneLabel = sceneLabelSprite(); camera.add(sceneLabel);
  const fade = new THREE.Mesh(new THREE.PlaneGeometry(14, 9),
    new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: 0, depthTest: false, depthWrite: false }));
  fade.position.set(0, 0, -4.1); fade.renderOrder = 1001; camera.add(fade);

  scene.add(new THREE.HemisphereLight(0xdde8d6, 0x343c32, 2.1));
  const key = new THREE.DirectionalLight(0xffe6c1, 3.1);
  key.position.set(-5, 10, 6); key.castShadow = true; key.shadow.mapSize.set(1024, 1024); scene.add(key);
  const fill = new THREE.PointLight(0x8ea7bd, 32, 22);
  fill.position.set(6, 5, -4); scene.add(fill);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(36, 36),
    new THREE.MeshStandardMaterial({ color: 0x353c34, roughness: .95 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const grid = new THREE.GridHelper(36, 36, 0x64715e, 0x414b40);
  grid.position.y = .012; scene.add(grid);
  addBox(scene, [18, 5, .28], [0, 2.5, -7], 0x596052, false);
  addBox(scene, [.28, 5, 14], [-9, 2.5, 0], 0x596052, false);
  const platform = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.8, .3, 32),
    new THREE.MeshStandardMaterial({ color: 0x89916e, metalness: .25, roughness: .55 }));
  platform.position.set(5, .16, -3); platform.castShadow = true; scene.add(platform);
  addBox(scene, [3.5, .8, 2.2], [-4, .4, -2], 0x665747);
  const doorway = new THREE.Group();
  for (const [x, y, z, w, h, d] of [
    [-2.2, 1.3, -6.78, .16, 2.6, .3], [-.2, 1.3, -6.78, .16, 2.6, .3],
    [-1.2, 2.55, -6.78, 2.1, .16, .3],
  ]) {
    const part = new THREE.Mesh(new THREE.BoxGeometry(w, h, d),
      new THREE.MeshStandardMaterial({ color: 0x242a24, roughness: .8 }));
    part.position.set(x, y, z); doorway.add(part);
  }
  scene.add(doorway);
  const stageLight = new THREE.SpotLight(0xffd6a1, 65, 20, Math.PI / 5, .5, 1.2);
  stageLight.position.set(0, 7, 1); stageLight.target.position.set(0, 0, 0);
  scene.add(stageLight, stageLight.target);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(width, height, false);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  return { scene, camera, renderer, rigs: new Map(), titleSprite: title, sceneLabel, fadePlane: fade, assetObjects: new Map(), width, height };
}

export async function loadProductionAssets(stage: ProductionStage, clips: SceneClip[]): Promise<void> {
  const assets = new Map<string, SceneProductionAsset>();
  for (const clip of clips) {
    for (const asset of clip.production_assets || []) {
      if (asset.asset_id && asset.render_url) assets.set(asset.asset_id, asset);
    }
  }
  const loader = new GLTFLoader();
  for (const asset of assets.values()) {
    if (stage.assetObjects.has(asset.asset_id)) continue;
    const gltf = await loader.loadAsync(asset.render_url);
    const object = gltf.scene;
    object.name = "StoryForge asset " + asset.asset_id + " v" + asset.version;
    object.userData.storyForgeAsset = asset;
    object.visible = false;
    object.traverse(child => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    stage.scene.add(object);
    stage.assetObjects.set(asset.asset_id, object);
  }
}

function applyAssetTransform(object: THREE.Object3D, transform: SceneProductionAsset["transform"]): void {
  const position = vector(transform.position);
  const rotation = vector(transform.rotation);
  const scale = vector(transform.scale);
  object.position.copy(position || new THREE.Vector3());
  object.rotation.set(rotation?.x || 0, rotation?.y || 0, rotation?.z || 0);
  object.scale.copy(scale || new THREE.Vector3(1, 1, 1));
}

function vector(value: unknown): THREE.Vector3 | null {
  if (Array.isArray(value) && value.length >= 3) {
    const values = value.slice(0, 3).map(Number);
    return values.every(Number.isFinite) ? new THREE.Vector3(values[0], values[1], values[2]) : null;
  }
  if (value && typeof value === "object") {
    const item = value as Record<string, unknown>;
    const values = [item.x, item.y, item.z].map(Number);
    return values.every(Number.isFinite) ? new THREE.Vector3(values[0], values[1], values[2]) : null;
  }
  return null;
}

function eventTransform(event: SceneReplayEvent): Record<string, unknown> {
  const nested = event.payload.transform;
  return nested && typeof nested === "object" ? nested as Record<string, unknown> : event.payload;
}

function sampleTransform(events: SceneReplayEvent[], memberId: string, sourceMs: number): Record<string, unknown> {
  const samples = events.filter(event => event.event_type === "transform" && event.cast_member_instance_id === memberId);
  let previous: SceneReplayEvent | undefined;
  let next: SceneReplayEvent | undefined;
  for (const event of samples) {
    if (event.timestamp_ms <= sourceMs) previous = event;
    else { next = event; break; }
  }
  if (!previous) return {};
  const start = eventTransform(previous);
  if (!next) return start;
  const end = eventTransform(next);
  const amount = THREE.MathUtils.clamp((sourceMs - previous.timestamp_ms) /
    Math.max(1, next.timestamp_ms - previous.timestamp_ms), 0, 1);
  const result = { ...start };
  for (const key of ["position", "rotation", "scale"]) {
    const a = vector(start[key]); const b = vector(end[key]);
    if (a && b) result[key] = a.lerp(b, amount).toArray();
  }
  return result;
}

export function renderProductionClip(stage: ProductionStage, clip: SceneClip, localMs: number): HTMLCanvasElement {
  const members = clip.cast_members || [];
  const ids = members.map(member => member.id);
  if (ids.length !== stage.rigs.size || ids.some(id => !stage.rigs.has(id))) {
    for (const rig of stage.rigs.values()) {
      stage.scene.remove(rig);
      rig.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) {
          if (object instanceof THREE.Mesh) object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach(material => {
            if (material && "map" in material && material.map) material.map.dispose();
            material?.dispose();
          });
        }
      });
    }
    stage.rigs.clear();
    members.forEach((member, index) => {
      const name = member.character_name || member.character_name_snapshot ||
        member.actor_name || member.actor_name_snapshot || "Cast";
      const rig = createCharacterRig(index, members.length, name);
      stage.scene.add(rig); stage.rigs.set(member.id, rig);
    });
  }

  const sourceMs = Number(clip.in_ms || 0) + Math.max(0, localMs);
  const cameraEvents = (clip.events || []).filter(event => event.event_type === "camera" && event.timestamp_ms <= sourceMs);
  const cameraEvent = cameraEvents[cameraEvents.length - 1];
  const camera = { ...(clip.camera_snapshot || {}), ...(cameraEvent?.payload || {}) };
  const preset = String(camera.preset || "wide");
  const cameraPosition = vector(camera.position);
  stage.camera.position.copy(cameraPosition || new THREE.Vector3(...(CAMERA_POSITIONS[preset] || CAMERA_POSITIONS.wide)));
  stage.camera.lookAt(vector(camera.target) || new THREE.Vector3(0, 1, 0));
  stage.camera.updateMatrixWorld();

  for (const member of members) {
    const rig = stage.rigs.get(member.id)!;
    const basePosition = rig.userData.basePosition as THREE.Vector3;
    const baseRotation = rig.userData.baseRotation as THREE.Euler;
    const baseScale = rig.userData.baseScale as THREE.Vector3;
    const transform = sampleTransform(clip.events || [], member.id, sourceMs);
    const position = vector(transform.position);
    const rotation = vector(transform.rotation);
    const scale = vector(transform.scale);
    rig.position.copy(position || basePosition);
    rig.rotation.set(rotation?.x ?? baseRotation.x, rotation?.y ?? baseRotation.y, rotation?.z ?? baseRotation.z);
    rig.scale.copy(scale || baseScale);
  }
  const clipAssets = clip.production_assets || [];
  for (const object of stage.assetObjects.values()) object.visible = false;
  for (const member of members) {
    const model = clipAssets.find(asset => asset.target_type === "character" && asset.target_id === member.character_id);
    const rig = stage.rigs.get(member.id);
    if (!rig) continue;
    rig.traverse(object => {
      if (object instanceof THREE.Mesh && object.userData.isProceduralCharacterPart) object.visible = !model;
    });
    if (model) {
      const object = stage.assetObjects.get(model.asset_id);
      if (object) {
        applyAssetTransform(object, model.transform);
        object.position.add(rig.position);
        object.rotation.set(
          object.rotation.x + rig.rotation.x,
          object.rotation.y + rig.rotation.y,
          object.rotation.z + rig.rotation.z,
        );
        object.scale.multiply(rig.scale);
        object.visible = true;
      }
    }
  }
  for (const asset of clipAssets) {
    if (asset.target_type !== "location") continue;
    const object = stage.assetObjects.get(asset.asset_id);
    if (object && asset.target_id === clip.location_id) {
      applyAssetTransform(object, asset.transform);
      object.visible = true;
    }
  }
  updateSceneLabel(stage.sceneLabel, String(clip.scene_title || "Scene"));
  updateTitle(stage.titleSprite, String(clip.title_overlay || ""));
  stage.renderer.render(stage.scene, stage.camera);
  return stage.renderer.domElement;
}

export function disposeProductionStage(stage: ProductionStage): void {
  stage.renderer.dispose();
  stage.scene.traverse(object => {
    if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) {
      if (object instanceof THREE.Mesh) object.geometry.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach(material => {
        if (material && "map" in material && material.map) material.map.dispose();
        material?.dispose();
      });
    }
  });
}
