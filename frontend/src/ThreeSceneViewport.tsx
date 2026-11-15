import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type CastVisual = {
  id: string;
  character_name_snapshot: string;
  actor_name_snapshot: string;
  state_snapshot: Record<string, unknown>;
};

type Props = { castMembers: CastVisual[]; sceneTitle: string; cameraPreset: "wide" | "close" | "overhead" | "reverse" };

function makeLabel(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512; canvas.height = 96;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = "rgba(20, 25, 21, 0.86)";
    context.beginPath(); context.roundRect(8, 8, 496, 80, 16); context.fill();
    context.fillStyle = "#e8eddd"; context.font = "bold 34px Arial";
    context.textAlign = "center"; context.textBaseline = "middle";
    context.fillText(text.slice(0, 28), 256, 48);
  }
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false }));
  sprite.scale.set(2.8, .52, 1);
  return sprite;
}

function makeCharacter(index: number, total: number, label: string): THREE.Group {
  const group = new THREE.Group();
  const hue = (index * 0.19 + 0.08) % 1;
  const cloth = new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(hue, .32, .48), roughness: .82 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xb58c70, roughness: .9 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x292e2a, roughness: .95 });
  const add = (geometry: THREE.BufferGeometry, material: THREE.Material, position: [number, number, number]) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...position); mesh.castShadow = true; mesh.receiveShadow = true;
    group.add(mesh); return mesh;
  };
  add(new THREE.CylinderGeometry(.31, .4, .95, 12), cloth, [0, 1.35, 0]);
  add(new THREE.SphereGeometry(.28, 16, 12), skin, [0, 2.02, 0]);
  add(new THREE.CylinderGeometry(.12, .13, .72, 10), skin, [-.43, 1.35, 0]).rotation.z = -.24;
  add(new THREE.CylinderGeometry(.12, .13, .72, 10), skin, [.43, 1.35, 0]).rotation.z = .24;
  add(new THREE.CylinderGeometry(.14, .16, .82, 10), dark, [-.17, .45, 0]).rotation.z = -.04;
  add(new THREE.CylinderGeometry(.14, .16, .82, 10), dark, [.17, .45, 0]).rotation.z = .04;
  const labelSprite = makeLabel(label);
  labelSprite.position.set(0, 2.65, 0);
  group.add(labelSprite);
  const spacing = Math.max(2.2, Math.min(3.8, 10 / Math.max(1, total)));
  group.position.set((index - (total - 1) / 2) * spacing, 0, 0);
  return group;
}

export default function ThreeSceneViewport({ castMembers, sceneTitle, cameraPreset }: Props) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x161c18);
    scene.fog = new THREE.Fog(0x161c18, 18, 48);
    const camera = new THREE.PerspectiveCamera(44, 1, .1, 100);
    const cameraPositions = { wide: [8, 7, 11], close: [4, 3, 6], overhead: [0, 15, .1], reverse: [-8, 6, -10] } as const;
    camera.position.set(...cameraPositions[cameraPreset]);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x161c18);
    element.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1, 0);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI * .48;
    scene.add(new THREE.HemisphereLight(0xdde8d6, 0x343c32, 2.1));
    const key = new THREE.DirectionalLight(0xffe6c1, 3.1);
    key.position.set(-5, 10, 6); key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);
    const fill = new THREE.PointLight(0x8ea7bd, 32, 22);
    fill.position.set(6, 5, -4); scene.add(fill);

    const floor = new THREE.Mesh(new THREE.PlaneGeometry(36, 36), new THREE.MeshStandardMaterial({ color: 0x353c34, roughness: .95 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    const grid = new THREE.GridHelper(36, 36, 0x64715e, 0x414b40);
    grid.position.y = .012; scene.add(grid);
    const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x596052, roughness: .9 });
    const wall = new THREE.Mesh(new THREE.BoxGeometry(18, 5, .28), wallMaterial);
    wall.position.set(0, 2.5, -7); wall.receiveShadow = true; scene.add(wall);
    const sideWall = new THREE.Mesh(new THREE.BoxGeometry(.28, 5, 14), wallMaterial);
    sideWall.position.set(-9, 2.5, 0); sideWall.receiveShadow = true; scene.add(sideWall);
    const platform = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.8, .3, 32), new THREE.MeshStandardMaterial({ color: 0x89916e, metalness: .25, roughness: .55 }));
    platform.position.set(5, .16, -3); platform.castShadow = true; scene.add(platform);
    const plinth = new THREE.Mesh(new THREE.BoxGeometry(3.5, .8, 2.2), new THREE.MeshStandardMaterial({ color: 0x665747, roughness: .8 }));
    plinth.position.set(-4, .4, -2); plinth.castShadow = true; scene.add(plinth);
    const doorway = new THREE.Group();
    const trim = new THREE.MeshStandardMaterial({ color: 0x242a24, roughness: .8 });
    for (const [x, y, z, w, h, d] of [[-2.2,1.3,-6.78,.16,2.6,.3],[-.2,1.3,-6.78,.16,2.6,.3],[-1.2,2.55,-6.78,2.1,.16,.3]] as number[][]) {
      const part = new THREE.Mesh(new THREE.BoxGeometry(w,h,d), trim); part.position.set(x,y,z); doorway.add(part);
    }
    scene.add(doorway);
    const stageLight = new THREE.SpotLight(0xffd6a1, 65, 20, Math.PI / 5, .5, 1.2);
    stageLight.position.set(0, 7, 1); stageLight.target.position.set(0, 0, 0);
    scene.add(stageLight, stageLight.target);

    const rigs = castMembers.map((member, index) =>
      makeCharacter(index, castMembers.length, member.character_name_snapshot || member.actor_name_snapshot || "Cast")
    );
    rigs.forEach(rig => scene.add(rig));

    const resize = () => {
      const width = Math.max(1, element.clientWidth);
      const height = Math.max(220, element.clientHeight);
      camera.aspect = width / height; camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element); resize();
    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();
    return () => {
      cancelAnimationFrame(frame); observer.disconnect(); controls.dispose();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) {
          if (object instanceof THREE.Mesh) object.geometry.dispose();
          const material = object.material;
          if (Array.isArray(material)) material.forEach(item => item.dispose());
          else material?.dispose();
        }
      });
      renderer.dispose();
      if (element.contains(renderer.domElement)) element.removeChild(renderer.domElement);
    };
  }, [castMembers, sceneTitle, cameraPreset]);

  return <div className="production-viewport" ref={host} aria-label={`Three dimensional production set for ${sceneTitle}`} />;
}
