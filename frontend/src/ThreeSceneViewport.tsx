import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { createCharacterRig, type SceneProductionAsset } from "./productionScene";

type CastVisual = {
  id: string;
  character_name_snapshot: string;
  actor_name_snapshot: string;
  character_id?: string;
};

type ReplayEvent = {
  timestamp_ms: number;
  event_type: string;
  cast_member_instance_id: string | null;
  payload: Record<string, unknown>;
};
type CameraPreset = "wide" | "close" | "overhead" | "reverse";
type Props = {
  castMembers: CastVisual[];
  sceneTitle: string;
  cameraPreset: CameraPreset;
  replayEvents?: ReplayEvent[];
  playheadMs?: number;
  titleOverlay?: string;
  fadeOpacity?: number;
  onCanvasReady?: (canvas: HTMLCanvasElement | null) => void;
  productionAssets?: SceneProductionAsset[];
  sceneLocationId?: string | null;
};

const CAMERA_POSITIONS: Record<CameraPreset, [number, number, number]> = {
  wide: [8, 7, 11],
  close: [4, 3, 6],
  overhead: [0, 15, 0.1],
  reverse: [-8, 6, -10],
};

function makeTitleSprite(): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 220;
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: texture, transparent: true, depthTest: false, depthWrite: false,
  }));
  sprite.scale.set(6.2, 1.14, 1);
  sprite.position.set(0, -1.2, -4.4);
  sprite.renderOrder = 1000;
  sprite.userData.canvas = canvas;
  return sprite;
}

function updateTitleSprite(sprite: THREE.Sprite, text: string): void {
  const canvas = sprite.userData.canvas as HTMLCanvasElement;
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  if (text.trim()) {
    context.fillStyle = "rgba(8, 12, 9, 0.78)";
    context.beginPath();
    context.roundRect(28, 28, 1144, 164, 22);
    context.fill();
    context.fillStyle = "#f0f1e7";
    context.font = "600 58px Arial";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text.slice(0, 54), 600, 110);
  }
  sprite.visible = Boolean(text.trim());
  (sprite.material as THREE.SpriteMaterial).map!.needsUpdate = true;
}

const makeCharacter = createCharacterRig;

function disposeObject(root: THREE.Object3D): void {
  root.traverse((object) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) {
      if (object instanceof THREE.Mesh) object.geometry.dispose();
      const material = object.material;
      if (Array.isArray(material)) material.forEach((item) => {
        if ("map" in item && item.map) item.map.dispose();
        item.dispose();
      });
      else if (material) {
        if ("map" in material && material.map) material.map.dispose();
        material.dispose();
      }
    }
  });
}

function vectorFrom(value: unknown): THREE.Vector3 | null {
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

function eventTransform(event: ReplayEvent): Record<string, unknown> {
  const nested = event.payload.transform;
  return nested && typeof nested === "object" ? nested as Record<string, unknown> : event.payload;
}

function interpolateVector(previous: THREE.Vector3, next: THREE.Vector3 | null, amount: number): THREE.Vector3 {
  return next ? previous.clone().lerp(next, THREE.MathUtils.clamp(amount, 0, 1)) : previous;
}

export default function ThreeSceneViewport({
  castMembers,
  sceneTitle,
  cameraPreset,
  replayEvents = [],
  playheadMs = 0,
  titleOverlay = "",
  fadeOpacity = 0,
  onCanvasReady,
  productionAssets = [],
  sceneLocationId = null,
}: Props) {
  const host = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rigsRef = useRef<Map<string, THREE.Group>>(new Map());
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const titleSpriteRef = useRef<THREE.Sprite | null>(null);
  const fadePlaneRef = useRef<THREE.Mesh | null>(null);
  const onCanvasReadyRef = useRef(onCanvasReady);

  useEffect(() => { onCanvasReadyRef.current = onCanvasReady; }, [onCanvasReady]);

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x161c18);
    scene.fog = new THREE.Fog(0x161c18, 18, 48);
    const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 100);
    camera.position.set(...CAMERA_POSITIONS.wide);
    cameraRef.current = camera;
    scene.add(camera);

    const titleSprite = makeTitleSprite();
    camera.add(titleSprite);
    titleSpriteRef.current = titleSprite;
    const fadePlane = new THREE.Mesh(
      new THREE.PlaneGeometry(14, 9),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0, depthTest: false, depthWrite: false }),
    );
    fadePlane.position.set(0, 0, -4.1);
    fadePlane.renderOrder = 1001;
    camera.add(fadePlane);
    fadePlaneRef.current = fadePlane;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x161c18);
    element.appendChild(renderer.domElement);
    onCanvasReadyRef.current?.(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.target.set(0, 1, 0);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI * 0.48;

    scene.add(new THREE.HemisphereLight(0xdde8d6, 0x343c32, 2.1));
    const key = new THREE.DirectionalLight(0xffe6c1, 3.1);
    key.position.set(-5, 10, 6);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);
    const fill = new THREE.PointLight(0x8ea7bd, 32, 22);
    fill.position.set(6, 5, -4);
    scene.add(fill);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(36, 36),
      new THREE.MeshStandardMaterial({ color: 0x353c34, roughness: 0.95 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);
    const grid = new THREE.GridHelper(36, 36, 0x64715e, 0x414b40);
    grid.position.y = 0.012;
    scene.add(grid);
    const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x596052, roughness: 0.9 });
    const wall = new THREE.Mesh(new THREE.BoxGeometry(18, 5, 0.28), wallMaterial);
    wall.position.set(0, 2.5, -7);
    wall.receiveShadow = true;
    scene.add(wall);
    const sideWall = new THREE.Mesh(new THREE.BoxGeometry(0.28, 5, 14), wallMaterial);
    sideWall.position.set(-9, 2.5, 0);
    sideWall.receiveShadow = true;
    scene.add(sideWall);
    const platform = new THREE.Mesh(
      new THREE.CylinderGeometry(1.5, 1.8, 0.3, 32),
      new THREE.MeshStandardMaterial({ color: 0x89916e, metalness: 0.25, roughness: 0.55 }),
    );
    platform.position.set(5, 0.16, -3);
    platform.castShadow = true;
    scene.add(platform);
    const plinth = new THREE.Mesh(
      new THREE.BoxGeometry(3.5, 0.8, 2.2),
      new THREE.MeshStandardMaterial({ color: 0x665747, roughness: 0.8 }),
    );
    plinth.position.set(-4, 0.4, -2);
    plinth.castShadow = true;
    scene.add(plinth);

    const doorway = new THREE.Group();
    const trim = new THREE.MeshStandardMaterial({ color: 0x242a24, roughness: 0.8 });
    for (const [x, y, z, w, h, d] of [
      [-2.2, 1.3, -6.78, 0.16, 2.6, 0.3],
      [-0.2, 1.3, -6.78, 0.16, 2.6, 0.3],
      [-1.2, 2.55, -6.78, 2.1, 0.16, 0.3],
    ]) {
      const part = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), trim);
      part.position.set(x, y, z);
      doorway.add(part);
    }
    scene.add(doorway);
    const stageLight = new THREE.SpotLight(0xffd6a1, 65, 20, Math.PI / 5, 0.5, 1.2);
    stageLight.position.set(0, 7, 1);
    stageLight.target.position.set(0, 0, 0);
    scene.add(stageLight, stageLight.target);

    const resize = () => {
      const width = Math.max(1, element.clientWidth);
      const height = Math.max(220, element.clientHeight);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();

    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      rigsRef.current.clear();
      sceneRef.current = null;
      cameraRef.current = null;
      controlsRef.current = null;
      titleSpriteRef.current = null;
      fadePlaneRef.current = null;
      onCanvasReadyRef.current?.(null);
      disposeObject(scene);
      renderer.dispose();
      if (element.contains(renderer.domElement)) element.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    for (const rig of rigsRef.current.values()) {
      scene.remove(rig);
      disposeObject(rig);
    }
    const rigs = castMembers.map((member, index) =>
      makeCharacter(index, castMembers.length, member.character_name_snapshot || member.actor_name_snapshot || "Cast"),
    );
    rigs.forEach((rig) => scene.add(rig));
    rigsRef.current = new Map(castMembers.map((member, index) => [member.id, rigs[index]]));
  }, [castMembers]);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !productionAssets.length) return;
    let alive = true;
    const loader = new GLTFLoader();
    const loaded: THREE.Object3D[] = [];
    const applyTransform = (object: THREE.Object3D, transform: SceneProductionAsset["transform"]) => {
      const position = transform.position || [0, 0, 0];
      const rotation = transform.rotation || [0, 0, 0];
      const scale = transform.scale || [1, 1, 1];
      object.position.set(Number(position[0]), Number(position[1]), Number(position[2]));
      object.rotation.set(Number(rotation[0]), Number(rotation[1]), Number(rotation[2]));
      object.scale.set(Number(scale[0]), Number(scale[1]), Number(scale[2]));
    };
    Promise.all(productionAssets.map(async asset => {
      const gltf = await loader.loadAsync(asset.download_url || asset.render_url);
      const object = gltf.scene;
      if (!alive) { disposeObject(object); return; }
      object.name = "StoryForge asset " + asset.asset_id + " v" + asset.version;
      object.userData.storyForgeAsset = asset;
      object.traverse(child => {
        if (child instanceof THREE.Mesh) { child.castShadow = true; child.receiveShadow = true; }
      });
      applyTransform(object, asset.transform || {});
      if (asset.target_type === "character") {
        const member = castMembers.find(item => item.character_id === asset.target_id);
        const rig = member ? rigsRef.current.get(member.id) : null;
        if (!rig) return;
        rig.traverse(child => {
          if (child instanceof THREE.Mesh && child.userData.isProceduralCharacterPart) child.visible = false;
        });
        rig.add(object);
      } else if (asset.target_type === "location" && asset.target_id === sceneLocationId) {
        scene.add(object);
      }
      loaded.push(object);
    })).catch(() => undefined);
    return () => {
      alive = false;
      loaded.forEach(object => { object.parent?.remove(object); disposeObject(object); });
      rigsRef.current.forEach(rig => rig.traverse(child => {
        if (child instanceof THREE.Mesh && child.userData.isProceduralCharacterPart) child.visible = true;
      }));
    };
  }, [productionAssets, castMembers, sceneLocationId]);

  useEffect(() => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;
    const cameraEvents = replayEvents
      .filter((event) => event.event_type === "camera" && event.timestamp_ms <= playheadMs)
      .sort((a, b) => a.timestamp_ms - b.timestamp_ms);
    const latestCameraEvent = cameraEvents.length ? cameraEvents[cameraEvents.length - 1] : undefined;
    const payload = latestCameraEvent?.payload || {};
    const position = vectorFrom(payload.position);
    const target = vectorFrom(payload.target);
    if (position) camera.position.copy(position);
    else {
      const preset = typeof payload.preset === "string" && payload.preset in CAMERA_POSITIONS
        ? payload.preset as CameraPreset
        : cameraPreset;
      camera.position.set(...CAMERA_POSITIONS[preset]);
    }
    if (target) controls.target.copy(target);
    else controls.target.set(0, 1, 0);
    controls.update();
  }, [cameraPreset, replayEvents, playheadMs]);

  useEffect(() => {
    for (const [memberId, rig] of rigsRef.current.entries()) {
      const samples = replayEvents
        .filter((event) => event.event_type === "transform" && event.cast_member_instance_id === memberId)
        .sort((a, b) => a.timestamp_ms - b.timestamp_ms);
      const basePosition = rig.userData.basePosition as THREE.Vector3;
      const baseRotation = rig.userData.baseRotation as THREE.Euler;
      const baseScale = rig.userData.baseScale as THREE.Vector3;
      let previousIndex = -1;
      for (let index = 0; index < samples.length; index += 1) {
        if (samples[index].timestamp_ms <= playheadMs) previousIndex = index;
        else break;
      }
      const previous = previousIndex >= 0 ? samples[previousIndex] : null;
      const next = samples[previousIndex + 1] || null;
      const startTime = previous?.timestamp_ms ?? 0;
      const endTime = next?.timestamp_ms ?? startTime;
      const amount = endTime > startTime ? (playheadMs - startTime) / (endTime - startTime) : 1;
      const previousPayload = previous ? eventTransform(previous) : {};
      const nextPayload = next ? eventTransform(next) : {};
      const positionStart = vectorFrom(previousPayload.position) || basePosition;
      const rotationStart = vectorFrom(previousPayload.rotation) || new THREE.Vector3(baseRotation.x, baseRotation.y, baseRotation.z);
      const scaleStart = vectorFrom(previousPayload.scale) || baseScale;
      rig.position.copy(interpolateVector(positionStart, vectorFrom(nextPayload.position), amount));
      const rotation = interpolateVector(rotationStart, vectorFrom(nextPayload.rotation), amount);
      rig.rotation.set(rotation.x, rotation.y, rotation.z);
      rig.scale.copy(interpolateVector(scaleStart, vectorFrom(nextPayload.scale), amount));
    }
  }, [castMembers, playheadMs, replayEvents]);

  useEffect(() => {
    if (titleSpriteRef.current) updateTitleSprite(titleSpriteRef.current, titleOverlay);
  }, [titleOverlay]);

  useEffect(() => {
    const material = fadePlaneRef.current?.material;
    if (material && !Array.isArray(material)) material.opacity = THREE.MathUtils.clamp(fadeOpacity, 0, 1);
  }, [fadeOpacity]);

  return <div className="production-viewport" ref={host} aria-label={"Three dimensional production set for " + sceneTitle} />;
}
