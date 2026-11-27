import { useEffect, useRef } from "react";
import * as THREE from "three";
import { reconstructCanonicalSkeleton, type CanonicalSkeleton } from "./canonicalSkeleton";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { HumanoidRetargeter, type HumanoidRigProfile } from "./humanoidRetargeter";
import { detectHumanoidRigProfile, type HumanoidRigPreviewStatus } from "./humanoidRigProfiles";

type Point = { x: number; y: number; z: number } | null;
type Quaternion = { x: number; y: number; z: number; w: number } | null;
type Props = {
  characterName: string;
  head: Point;
  headOrientation: Quaternion;
  leftWrist: Point;
  rightWrist: Point;
  skeleton?: CanonicalSkeleton | null;
  modelUrl?: string;
  onRigStatus?: (status: HumanoidRigPreviewStatus) => void;\n  profileOverride?: HumanoidRigProfile | null;\n  onProfileDetected?: (profile: HumanoidRigProfile) => void;
};

type AvatarParts = {
  root: THREE.Group;
  torso: THREE.Mesh;
  pelvis: THREE.Mesh;
  head: THREE.Mesh;
  leftUpperArm: THREE.Mesh;
  leftLowerArm: THREE.Mesh;
  rightUpperArm: THREE.Mesh;
  rightLowerArm: THREE.Mesh;
  leftHand: THREE.Mesh;
  rightHand: THREE.Mesh;
  leftLeg: THREE.Mesh;
  rightLeg: THREE.Mesh;
  label: THREE.Sprite;
};

function makeMaterial(color: number, roughness = 0.78): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness });
}

function makeSegment(material: THREE.Material, radius: number): THREE.Mesh {
  return new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, 1, 12), material);
}

function placeSegment(mesh: THREE.Mesh, start: THREE.Vector3, end: THREE.Vector3): void {
  const direction = new THREE.Vector3().subVectors(end, start);
  mesh.position.copy(start).add(end).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
  mesh.scale.set(1, Math.max(0.001, direction.length()), 1);
}

function makeLabel(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 640;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = "rgba(12,18,14,.82)";
    context.beginPath();
    context.roundRect(8, 8, 624, 112, 18);
    context.fill();
    context.fillStyle = "#e8efdf";
    context.font = "600 42px Arial";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text.slice(0, 28), 320, 64);
  }
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false }));
  sprite.scale.set(1.9, 0.38, 1);
  sprite.position.set(0, 2.45, 0);
  return sprite;
}

function createAvatar(name: string): AvatarParts {
  const root = new THREE.Group();
  const cloth = makeMaterial(0x668b76);
  const skin = makeMaterial(0xc59b7b);
  const trousers = makeMaterial(0x303d50);
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.27, 0.55, 5, 12), cloth);
  torso.position.y = 1.13;
  const pelvis = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.25, 0.28), trousers);
  pelvis.position.y = 0.78;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.19, 20, 16), skin);
  head.position.y = 1.68;
  const leftUpperArm = makeSegment(cloth, 0.075);
  const leftLowerArm = makeSegment(skin, 0.06);
  const rightUpperArm = makeSegment(cloth, 0.075);
  const rightLowerArm = makeSegment(skin, 0.06);
  const leftHand = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), skin);
  const rightHand = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), skin);
  const leftLeg = makeSegment(trousers, 0.095);
  const rightLeg = makeSegment(trousers, 0.095);
  const label = makeLabel(name);
  root.add(torso, pelvis, head, leftUpperArm, leftLowerArm, rightUpperArm, rightLowerArm, leftHand, rightHand, leftLeg, rightLeg, label);
  return { root, torso, pelvis, head, leftUpperArm, leftLowerArm, rightUpperArm, rightLowerArm, leftHand, rightHand, leftLeg, rightLeg, label };
}

function updateAvatar(parts: AvatarParts, props: Props): void {
  const skeleton = props.skeleton ?? reconstructCanonicalSkeleton(props.head, props.leftWrist, props.rightWrist);
  const joints = skeleton.joints;
  const v = (name: keyof typeof joints) => {
    const p = joints[name]!;
    return new THREE.Vector3(p.x, p.y, p.z);
  };
  const pelvis = v("pelvis"), chest = v("chest");
  const head = v("head");
  parts.torso.position.copy(chest);
  parts.torso.position.y = (pelvis.y + chest.y) / 2;
  parts.torso.position.x = chest.x;
  parts.torso.position.z = chest.z;
  parts.pelvis.position.copy(pelvis);
  parts.head.position.copy(head);
  if (props.headOrientation) {
    parts.head.quaternion.set(props.headOrientation.x, props.headOrientation.y, props.headOrientation.z, props.headOrientation.w);
  }
  const leftShoulder=v("left_shoulder"), rightShoulder=v("right_shoulder");
  const leftElbow=v("left_elbow"), rightElbow=v("right_elbow");
  const leftWrist=v("left_wrist"), rightWrist=v("right_wrist");
  placeSegment(parts.leftUpperArm,leftShoulder,leftElbow);
  placeSegment(parts.leftLowerArm,leftElbow,leftWrist);
  placeSegment(parts.rightUpperArm,rightShoulder,rightElbow);
  placeSegment(parts.rightLowerArm,rightElbow,rightWrist);
  parts.leftHand.position.copy(leftWrist);
  parts.rightHand.position.copy(rightWrist);
  placeSegment(parts.leftLeg,v("left_hip"),v("left_ankle"));
  placeSegment(parts.rightLeg,v("right_hip"),v("right_ankle"));
  parts.label.position.set(pelvis.x, 2.45, pelvis.z);
}

export default function LiveAvatarPreview(props: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const partsRef = useRef<AvatarParts | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const modelRef = useRef<THREE.Object3D | null>(null);
  const retargeterRef = useRef<HumanoidRetargeter | null>(null);
  const latestPropsRef = useRef(props);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x151d17);
    scene.fog = new THREE.Fog(0x151d17, 7, 18);
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
    camera.position.set(2.7, 2.35, 4.8);
    camera.lookAt(0, 1.15, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.1, 0);
    controls.enableDamping = true;
    controls.minDistance = 2.2;
    controls.maxDistance = 9;
    scene.add(new THREE.HemisphereLight(0xe5eee4, 0x333a34, 2.2));
    const key = new THREE.DirectionalLight(0xffe2c2, 2.4);
    key.position.set(-3, 6, 4);
    scene.add(key);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.MeshStandardMaterial({ color: 0x283229, roughness: 1 }));
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.015;
    scene.add(floor);
    scene.add(new THREE.GridHelper(12, 24, 0x56634f, 0x354035));
    const parts = createAvatar(props.characterName);
    partsRef.current = parts;
    scene.add(parts.root);
    const resize = () => {
      const width = Math.max(1, host.clientWidth);
      const height = Math.max(200, host.clientHeight);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
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
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) {
          if (object instanceof THREE.Mesh) object.geometry.dispose();
          const material = object.material;
          if (Array.isArray(material)) material.forEach(item => item.dispose());
          else if (material) material.dispose();
        }
      });
      renderer.dispose();
      if (host.contains(renderer.domElement)) host.removeChild(renderer.domElement);
      if (modelRef.current) {
        modelRef.current.parent?.remove(modelRef.current);
        modelRef.current = null;
      }
      retargeterRef.current?.reset();
      retargeterRef.current = null;
      sceneRef.current = null;
      partsRef.current = null;
    };
    // The viewport is recreated only when the component mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    latestPropsRef.current = props;
    const pose = props.skeleton ?? reconstructCanonicalSkeleton(props.head, props.leftWrist, props.rightWrist);
    const parts = partsRef.current;
    if (parts) updateAvatar(parts, props);
    try {
      retargeterRef.current?.apply(pose);
    } catch {
      // Keep the procedural fallback visible if a malformed or incompatible pose arrives.
    }
  }, [props.characterName, props.head, props.headOrientation, props.leftWrist, props.rightWrist, props.skeleton]);

  useEffect(() => {
    let alive = true;
    const scene = sceneRef.current;
    if (!scene || !props.modelUrl) {
      props.onRigStatus?.({ message: "No bound character model · procedural preview", boneNames: [], matchedSegments: [], missingSegments: [] });
      retargeterRef.current?.reset();
      retargeterRef.current = null;
      if (modelRef.current) {
        modelRef.current.parent?.remove(modelRef.current);
        modelRef.current = null;
      }
      if (partsRef.current) partsRef.current.root.visible = true;
      return;
    }
    props.onRigStatus?.({ message: "Loading character rig…", boneNames: [], matchedSegments: [], missingSegments: [] });
    const loader = new GLTFLoader();
    loader.load(props.modelUrl, gltf => {
      if (!alive) {
        gltf.scene.traverse(object => {
          if (object instanceof THREE.Mesh) {
            object.geometry.dispose();
            const materials = Array.isArray(object.material) ? object.material : [object.material];
            materials.forEach(material => material.dispose());
          }
        });
        return;
      }
      if (modelRef.current) {
        modelRef.current.parent?.remove(modelRef.current);
        modelRef.current = null;
      }
      const model = gltf.scene;
      model.name = "StoryForge retargeted character";
      model.traverse(object => {
        if (object instanceof THREE.Mesh) {
          object.castShadow = true;
          object.receiveShadow = true;
        }
      });
      const bounds = new THREE.Box3().setFromObject(model);
      const size = new THREE.Vector3();
      bounds.getSize(size);
      const height = size.y > 0.05 ? size.y : 1.7;
      const detection = detectHumanoidRigProfile(model);
      const profile = { ...(props.profileOverride || detection.profile), targetHeightM: height, fitCanonicalHeight: true };\n      props.onProfileDetected?.(detection.profile);
      const retargeter = new HumanoidRetargeter(model, profile);
      const fittedHeight = height * (1.7 / height);
      model.position.y -= bounds.min.y * (fittedHeight / height);
      scene.add(model);
      modelRef.current = model;
      retargeterRef.current = retargeter;
      model.visible = retargeter.boundBoneCount > 0;
      if (partsRef.current) partsRef.current.root.visible = retargeter.boundBoneCount === 0;
      const boundBoneNames = new Set(profile.bindings
        .map(binding => binding.bone)
        .filter(name => !retargeter.missingBones.includes(name)));
      const matchedSegments = profile.bindings
        .filter(binding => boundBoneNames.has(binding.bone))
        .map(binding => binding.start + " → " + binding.end);
      const missingSegments = [
        ...detection.missingSegments,
        ...profile.bindings
          .filter(binding => !boundBoneNames.has(binding.bone))
          .map(binding => binding.start + " → " + binding.end),
      ];
      if (retargeter.boundBoneCount > 0) {
        const coverage = retargeter.boundBoneCount + "/" + (detection.matchedSegments.length + detection.missingSegments.length);
        props.onRigStatus?.({
          message: detection.profile.label + " rig · " + coverage + " segments mapped",
          boneNames: detection.boneNames,
          matchedSegments,
          missingSegments,
        });
      } else {
        props.onRigStatus?.({
          message: "No compatible humanoid bones detected · procedural preview",
          boneNames: detection.boneNames,
          matchedSegments: [],
          missingSegments: detection.missingSegments,
        });
      }
      if (retargeter.boundBoneCount > 0) {
        retargeter.apply(latestPropsRef.current.skeleton ?? reconstructCanonicalSkeleton(
          latestPropsRef.current.head, latestPropsRef.current.leftWrist, latestPropsRef.current.rightWrist,
        ));
      }
    }, undefined, () => {
      if (alive) {
        if (partsRef.current) partsRef.current.root.visible = true;
        props.onRigStatus?.({ message: "Could not load character model · procedural preview", boneNames: [], matchedSegments: [], missingSegments: [] });
      }
    });
    return () => { alive = false; };
  }, [props.modelUrl, props.profileOverride]);

  return <div className="live-avatar-preview" ref={hostRef} aria-label="Live tracked avatar preview" />;
}
