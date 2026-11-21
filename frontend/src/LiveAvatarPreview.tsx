import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Point = { x: number; y: number; z: number } | null;
type Quaternion = { x: number; y: number; z: number; w: number } | null;
type Props = {
  characterName: string;
  head: Point;
  headOrientation: Quaternion;
  leftWrist: Point;
  rightWrist: Point;
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
  const rootX = props.head?.x ?? 0;
  const rootZ = props.head?.z ?? 0;
  parts.root.position.set(0, 0, 0);
  parts.torso.position.set(rootX, 1.13, rootZ);
  parts.pelvis.position.set(rootX, 0.78, rootZ);
  parts.label.position.set(rootX, 2.45, rootZ);
  const headPosition = props.head
    ? new THREE.Vector3(props.head.x, props.head.y, props.head.z)
    : new THREE.Vector3(rootX, 1.68, rootZ);
  parts.head.position.copy(headPosition);
  if (props.headOrientation) {
    parts.head.quaternion.set(props.headOrientation.x, props.headOrientation.y, props.headOrientation.z, props.headOrientation.w);
  }
  const leftShoulder = new THREE.Vector3(rootX - 0.25, 1.42, rootZ);
  const rightShoulder = new THREE.Vector3(rootX + 0.25, 1.42, rootZ);
  const leftWrist = props.leftWrist
    ? new THREE.Vector3(props.leftWrist.x, props.leftWrist.y, props.leftWrist.z)
    : new THREE.Vector3(rootX - 0.48, 1.12, rootZ + 0.04);
  const rightWrist = props.rightWrist
    ? new THREE.Vector3(props.rightWrist.x, props.rightWrist.y, props.rightWrist.z)
    : new THREE.Vector3(rootX + 0.48, 1.12, rootZ + 0.04);
  const leftElbow = leftShoulder.clone().lerp(leftWrist, 0.52).add(new THREE.Vector3(-0.08, 0.03, 0.08));
  const rightElbow = rightShoulder.clone().lerp(rightWrist, 0.52).add(new THREE.Vector3(0.08, 0.03, 0.08));
  placeSegment(parts.leftUpperArm, leftShoulder, leftElbow);
  placeSegment(parts.leftLowerArm, leftElbow, leftWrist);
  placeSegment(parts.rightUpperArm, rightShoulder, rightElbow);
  placeSegment(parts.rightLowerArm, rightElbow, rightWrist);
  parts.leftHand.position.copy(leftWrist);
  parts.rightHand.position.copy(rightWrist);
  placeSegment(parts.leftLeg, new THREE.Vector3(rootX - 0.14, 0.76, rootZ), new THREE.Vector3(rootX - 0.14, 0.12, rootZ));
  placeSegment(parts.rightLeg, new THREE.Vector3(rootX + 0.14, 0.76, rootZ), new THREE.Vector3(rootX + 0.14, 0.12, rootZ));
}

export default function LiveAvatarPreview(props: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const partsRef = useRef<AvatarParts | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x151d17);
    scene.fog = new THREE.Fog(0x151d17, 7, 18);
    sceneRef.current = scene;
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
      partsRef.current = null;
      sceneRef.current = null;
    };
    // The viewport is recreated only when the component mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const parts = partsRef.current;
    if (parts) updateAvatar(parts, props);
  }, [props.characterName, props.head, props.headOrientation, props.leftWrist, props.rightWrist]);

  return <div className="live-avatar-preview" ref={hostRef} aria-label="Live tracked avatar preview" />;
}
