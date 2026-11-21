import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import LiveAvatarPreview from "./LiveAvatarPreview";

type Vec3 = { x: number; y: number; z: number };
type Quaternion = { x: number; y: number; z: number; w: number };
type XRSpaceLike = XRReferenceSpace;
type XRFrameLike = XRFrame;
type XRSessionLike = XRSession;
type XRSystemLike = XRSystem;

type TrackingState = {
  head: Vec3 | null;
  headOrientation: Quaternion | null;
  leftWrist: Vec3 | null;
  rightWrist: Vec3 | null;
  leftIndex: Vec3 | null;
  rightIndex: Vec3 | null;
  tracking: boolean;
};
type Calibration = { origin: Vec3; yaw: number };
type CaptureCastMember = { id: string; character_name_snapshot: string; actor_name_snapshot: string };
type MappedPoint = { x: number; y: number; z: number };

const EMPTY: TrackingState = {
  head: null, headOrientation: null, leftWrist: null, rightWrist: null,
  leftIndex: null, rightIndex: null, tracking: false,
};

function rotateToActorSpace(dx: number, dz: number, yaw: number): { x: number; z: number } {
  const cosine = Math.cos(yaw);
  const sine = Math.sin(yaw);
  return { x: dx * cosine - dz * sine, z: dx * sine + dz * cosine };
}

function mapPoint(point: Vec3 | null, calibration: Calibration | null,
                  physicalWidth: number, physicalDepth: number,
                  virtualWidth: number, virtualDepth: number): MappedPoint | null {
  if (!point || !calibration) return null;
  const local = rotateToActorSpace(point.x - calibration.origin.x, point.z - calibration.origin.z, calibration.yaw);
  return {
    x: local.x * virtualWidth / physicalWidth,
    y: point.y,
    z: local.z * virtualDepth / physicalDepth,
  };
}

function insideZone(point: MappedPoint | null, virtualWidth: number, virtualDepth: number): boolean {
  return !!point && Math.abs(point.x) <= virtualWidth / 2 && Math.abs(point.z) <= virtualDepth / 2;
}

function percent(value: number, extent: number): number {
  return Math.max(0, Math.min(100, 50 + value / extent * 100));
}

export default function MotionCaptureSetup({ sceneRunId, castMembers }: { sceneRunId: string; castMembers: CaptureCastMember[] }) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const zoneGroupRef = useRef<THREE.Group | null>(null);
  const markerRefs = useRef<{ head: THREE.Mesh; left: THREE.Mesh; right: THREE.Mesh } | null>(null);
  const boundaryRefs = useRef<{ physical: THREE.LineLoop; virtual: THREE.LineLoop } | null>(null);
  const sessionRef = useRef<XRSessionLike | null>(null);
  const referenceSpaceRef = useRef<XRSpaceLike | null>(null);
  const calibrationRef = useRef<Calibration | null>(null);
  const calibrationsByCastMemberRef = useRef<Record<string, Calibration>>({});
  const [selectedCastMemberId, setSelectedCastMemberId] = useState(castMembers[0]?.id || "");
  const latestRef = useRef<TrackingState>(EMPTY);
  const lastUiUpdateRef = useRef(0);
  const [tracking, setTracking] = useState<TrackingState>(EMPTY);
  const [calibrated, setCalibrated] = useState(false);
  const [supported, setSupported] = useState<boolean | null>(null);
  const [physicalWidth, setPhysicalWidth] = useState(2.5);
  const [physicalDepth, setPhysicalDepth] = useState(2.5);
  const [virtualWidth, setVirtualWidth] = useState(2.5);
  const [virtualDepth, setVirtualDepth] = useState(2.5);
  const [status, setStatus] = useState("Not connected");
  const [error, setError] = useState("");

  useEffect(() => {
    const host = viewportRef.current;
    if (!host) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111711);
    const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
    camera.position.set(0, 2.2, 5.5);
    camera.lookAt(0, 1, 0);
    cameraRef.current = camera;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(host.clientWidth || 640, 260);
    renderer.xr.enabled = true;
    renderer.xr.setReferenceSpaceType("local-floor");
    host.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    scene.add(new THREE.HemisphereLight(0xdde8d6, 0x343c32, 2));
    const key = new THREE.DirectionalLight(0xffe6c1, 2.2);
    key.position.set(-3, 7, 4);
    scene.add(key);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ color: 0x222b22, roughness: 1 }));
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.015;
    scene.add(floor);
    const zone = new THREE.Group();
    scene.add(zone);
    zoneGroupRef.current = zone;

    const addBoundary = (width: number, depth: number, color: number, y: number) => {
      const points = [
        new THREE.Vector3(-width / 2, y, -depth / 2),
        new THREE.Vector3(width / 2, y, -depth / 2),
        new THREE.Vector3(width / 2, y, depth / 2),
        new THREE.Vector3(-width / 2, y, depth / 2),
      ];
      const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color }));
      zone.add(line);
      return line;
    };
    boundaryRefs.current = {
      physical: addBoundary(physicalWidth, physicalDepth, 0x9fc56e, 0.025),
      virtual: addBoundary(virtualWidth, virtualDepth, 0x65b5e8, 0.04),
    };
    const grid = new THREE.GridHelper(12, 24, 0x53634d, 0x354334);
    grid.position.y = 0.005;
    zone.add(grid);
    const marker = (color: number, radius: number) => {
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 16, 12), new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.15 }));
      mesh.visible = false;
      zone.add(mesh);
      return mesh;
    };
    const headMarker = marker(0xf0cf79, 0.13);
    const leftMarker = marker(0x70b9e8, 0.09);
    const rightMarker = marker(0xc18be8, 0.09);
    markerRefs.current = { head: headMarker, left: leftMarker, right: rightMarker };
    renderer.setAnimationLoop(() => renderer.render(scene, camera));

    const resize = () => {
      if (!host.clientWidth) return;
      camera.aspect = host.clientWidth / 260;
      camera.updateProjectionMatrix();
      renderer.setSize(host.clientWidth, 260);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    return () => {
      observer.disconnect();
      renderer.setAnimationLoop(null);
      renderer.dispose();
      host.removeChild(renderer.domElement);
      rendererRef.current = null;
      cameraRef.current = null;
      zoneGroupRef.current = null;
      markerRefs.current = null;
      boundaryRefs.current = null;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const xr = (navigator as Navigator & { xr?: XRSystemLike }).xr;
    if (!xr) { setSupported(false); return; }
    xr.isSessionSupported?.("immersive-vr")
      .then(value => { if (active) setSupported(value); })
      .catch(() => { if (active) setSupported(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => () => {
    const session = sessionRef.current;
    sessionRef.current = null;
    if (session) void session.end().catch(() => undefined);
  }, []);

  async function connect() {
    setError("");
    const xr = (navigator as Navigator & { xr?: XRSystemLike }).xr;
    if (!xr) { setError("WebXR is unavailable in this browser. Open StoryForge in a WebXR-compatible browser on the headset."); return; }
    let pendingSession: XRSessionLike | null = null;
    try {
      const session = await xr.requestSession("immersive-vr", {
        requiredFeatures: ["local-floor"],
        optionalFeatures: ["hand-tracking"],
      });
      pendingSession = session;
      const referenceSpace = await session.requestReferenceSpace("local-floor");
      cameraRef.current?.position.set(0, 0, 0);
      cameraRef.current?.rotation.set(0, 0, 0);
      await rendererRef.current?.xr.setSession(session as never);
      sessionRef.current = session;
      referenceSpaceRef.current = referenceSpace;
      setStatus("Headset connected · waiting for tracking");
      session.addEventListener("end", () => {
        if (sessionRef.current === session) sessionRef.current = null;
        referenceSpaceRef.current = null;
        latestRef.current = EMPTY;
        calibrationRef.current = null;
        calibrationsByCastMemberRef.current = {};
        setCalibrated(false);
        cameraRef.current?.position.set(0, 2.2, 5.5);
        cameraRef.current?.lookAt(0, 1, 0);
        setTracking(EMPTY);
        setStatus("Disconnected");
      }, { once: true });

      const tick = (_time: number, frame: XRFrameLike) => {
        if (sessionRef.current !== session) return;
        const space = referenceSpaceRef.current;
        const viewer = space ? frame.getViewerPose(space) : null;
        if (viewer && space) {
          const next: TrackingState = { ...EMPTY, tracking: true, head: viewer.transform.position, headOrientation: viewer.transform.orientation };
          for (const source of Array.from(session.inputSources)) {
            if (!source.hand) continue;
            const side = source.handedness === "left" ? "left" : source.handedness === "right" ? "right" : null;
            if (!side) continue;
            const wrist = source.hand.get("wrist");
            const index = source.hand.get("index-finger-tip");
            const getJointPose = typeof frame.getJointPose === "function" ? frame.getJointPose.bind(frame) : null;
            const wristPose = wrist && getJointPose ? getJointPose(wrist, space) : null;
            const indexPose = index && getJointPose ? getJointPose(index, space) : null;
            if (side === "left") {
              next.leftWrist = wristPose?.transform.position || null;
              next.leftIndex = indexPose?.transform.position || null;
            } else {
              next.rightWrist = wristPose?.transform.position || null;
              next.rightIndex = indexPose?.transform.position || null;
            }
          }
          latestRef.current = next;
          if (_time - lastUiUpdateRef.current >= 80) {
            lastUiUpdateRef.current = _time;
            setTracking(next);
          }
          setStatus(next.leftWrist || next.rightWrist ? "Head and hand tracking active" : "Head tracking active · enable hand tracking");
        } else {
          latestRef.current = EMPTY;
          if (_time - lastUiUpdateRef.current >= 80) {
            lastUiUpdateRef.current = _time;
            setTracking(EMPTY);
          }
          setStatus("Head tracking temporarily unavailable");
        }
        session.requestAnimationFrame(tick);
      };
      session.requestAnimationFrame(tick);
    } catch (cause) {
      if (pendingSession) await pendingSession.end().catch(() => undefined);
      await rendererRef.current?.xr.setSession(null).catch(() => undefined);
      cameraRef.current?.position.set(0, 2.2, 5.5);
      cameraRef.current?.lookAt(0, 1, 0);
      setError(cause instanceof Error ? cause.message : "Could not start the WebXR session.");
      setStatus("Connection failed");
    }
  }

  async function disconnect() {
    const session = sessionRef.current;
    sessionRef.current = null;
    referenceSpaceRef.current = null;
    if (session) await session.end().catch(() => undefined);
    await rendererRef.current?.xr.setSession(null);
    cameraRef.current?.position.set(0, 2.2, 5.5);
    cameraRef.current?.lookAt(0, 1, 0);
    latestRef.current = EMPTY;
    calibrationRef.current = null;
    calibrationsByCastMemberRef.current = {};
    setCalibrated(false);
    setTracking(EMPTY);
    setStatus("Disconnected");
  }

  function calibrate() {
    const head = latestRef.current.head;
    if (!head) { setError("Head tracking has not supplied a pose yet."); return; }
    const orientation = latestRef.current.headOrientation;
    if (!orientation) { setError("Head orientation is not available yet."); return; }
    const { x, y, z, w } = orientation;
    const yaw = Math.atan2(2 * (w * y + x * z), 1 - 2 * (y * y + z * z));
    calibrationRef.current = { origin: { x: head.x, y: 0, z: head.z }, yaw };
    if (selectedCastMemberId) calibrationsByCastMemberRef.current[selectedCastMemberId] = calibrationRef.current;
    zoneGroupRef.current?.position.set(head.x, 0, head.z);
    zoneGroupRef.current?.rotation.set(0, yaw, 0);
    setCalibrated(true);
    setError("");
    setStatus("Actor zone calibrated · move within the marked square");
  }

  function selectCastMember(id: string) {
    setSelectedCastMemberId(id);
    const saved = calibrationsByCastMemberRef.current[id] || null;
    calibrationRef.current = saved;
    setCalibrated(!!saved);
    zoneGroupRef.current?.position.set(saved?.origin.x || 0, 0, saved?.origin.z || 0);
    zoneGroupRef.current?.rotation.set(0, saved?.yaw || 0, 0);
  }

  const calibration = calibrationRef.current;
  const head = mapPoint(tracking.head, calibration, physicalWidth, physicalDepth, virtualWidth, virtualDepth);
  const left = mapPoint(tracking.leftWrist, calibration, physicalWidth, physicalDepth, virtualWidth, virtualDepth);
  const right = mapPoint(tracking.rightWrist, calibration, physicalWidth, physicalDepth, virtualWidth, virtualDepth);
  const outOfBounds = calibrated && head && !insideZone(head, virtualWidth, virtualDepth);

  useEffect(() => {
    const boundaries = boundaryRefs.current;
    if (!boundaries) return;
    const update = (line: THREE.LineLoop, width: number, depth: number) => {
      line.geometry.dispose();
      line.geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-width / 2, line === boundaries.physical ? 0.025 : 0.04, -depth / 2),
        new THREE.Vector3(width / 2, line === boundaries.physical ? 0.025 : 0.04, -depth / 2),
        new THREE.Vector3(width / 2, line === boundaries.physical ? 0.025 : 0.04, depth / 2),
        new THREE.Vector3(-width / 2, line === boundaries.physical ? 0.025 : 0.04, depth / 2),
      ]);
    };
    update(boundaries.physical, physicalWidth, physicalDepth);
    update(boundaries.virtual, virtualWidth, virtualDepth);
  }, [physicalWidth, physicalDepth, virtualWidth, virtualDepth]);

  useEffect(() => {
    const markers = markerRefs.current;
    if (!markers) return;
    markers.head.visible = !!head;
    markers.left.visible = !!left;
    markers.right.visible = !!right;
    if (head) markers.head.position.set(head.x, head.y, head.z);
    if (left) markers.left.position.set(left.x, left.y, left.z);
    if (right) markers.right.position.set(right.x, right.y, right.z);
  }, [tracking, calibrated, physicalWidth, physicalDepth, virtualWidth, virtualDepth]);

  return <section className="production-panel motion-capture-panel">
    <div className="casting-panel-heading">
      <div><div className="section-kicker">M2.3 · ROOM-SCALE CAPTURE</div><h3>Actor capture setup</h3></div>
      <span className={`production-status ${tracking.tracking ? "running" : "prepared"}`}>{tracking.tracking ? "tracking" : "standby"}</span>
    </div>
    <p className="muted-note">Scene run {sceneRunId.slice(0, 8)} · Connect a Quest headset to inspect room-scale head and hand tracking before recording a body take.</p>
    <div className="motion-capture-controls">
      <div className="motion-capture-actions">
        {!sessionRef.current
          ? <button type="button" className="primary-button" onClick={connect} disabled={supported === false}>Connect Quest</button>
          : <button type="button" className="secondary-button" onClick={disconnect}>Disconnect</button>}
        <span className="muted-note">{supported === null ? "Checking WebXR support…" : supported ? status : "Immersive WebXR is not available here."}</span>
      </div>
      {error && <div className="casting-alert error">{error}</div>}
      <label className="motion-capture-actor-select">Actor / character<select value={selectedCastMemberId} onChange={event => selectCastMember(event.target.value)}><option value="">Choose a cast member…</option>{castMembers.map(member => <option key={member.id} value={member.id}>{member.character_name_snapshot} · {member.actor_name_snapshot}</option>)}</select></label>
      <div className="motion-capture-calibration-actions"><button type="button" className="secondary-button" onClick={calibrate} disabled={!tracking.head || !selectedCastMemberId}>Calibrate zone from current position</button><button type="button" className="quiet-button" onClick={() => { calibrationRef.current = null; if (selectedCastMemberId) delete calibrationsByCastMemberRef.current[selectedCastMemberId]; setCalibrated(false); zoneGroupRef.current?.position.set(0, 0, 0); zoneGroupRef.current?.rotation.set(0, 0, 0); }}>Reset calibration</button><span className="muted-note">{calibrated ? "Calibrated to actor-facing direction" : "Calibration required before measuring boundaries"}</span></div>
      <div className="motion-capture-dimensions">
        <label>Physical width (m)<input type="number" min="1" max="8" step="0.1" value={physicalWidth} onChange={event => setPhysicalWidth(Math.max(1, Math.min(8, Number(event.target.value) || 1)))} /></label>
        <label>Physical depth (m)<input type="number" min="1" max="8" step="0.1" value={physicalDepth} onChange={event => setPhysicalDepth(Math.max(1, Math.min(8, Number(event.target.value) || 1)))} /></label>
        <label>Virtual width (m)<input type="number" min="1" max="30" step="0.1" value={virtualWidth} onChange={event => setVirtualWidth(Math.max(1, Math.min(30, Number(event.target.value) || 1)))} /></label>
        <label>Virtual depth (m)<input type="number" min="1" max="30" step="0.1" value={virtualDepth} onChange={event => setVirtualDepth(Math.max(1, Math.min(30, Number(event.target.value) || 1)))} /></label>
      </div>
      <div className="motion-capture-preview" ref={viewportRef} aria-label="Live room-scale capture preview" />
      <div className="motion-capture-avatar-preview">
        <div className="motion-capture-zone-heading"><strong>Live avatar preview</strong><span>{tracking.tracking ? "Live tracking" : "Waiting for tracking"}</span></div>
        <LiveAvatarPreview
          key={selectedCastMemberId}
          characterName={castMembers.find(member => member.id === selectedCastMemberId)?.character_name_snapshot || "Performer"}
          head={head}
          headOrientation={tracking.headOrientation}
          leftWrist={left}
          rightWrist={right}
        />
        <p className="muted-note">Head and tracked wrists drive the preview. Elbows and lower body are provisional procedural estimates, not captured full-body motion.</p>
      </div>
      <div className="motion-capture-zone">
        <div className="motion-capture-zone-heading"><strong>Actor floor zone · top view</strong><span>{physicalWidth.toFixed(1)} × {physicalDepth.toFixed(1)} m</span></div>
        <div className="motion-capture-zone-map" aria-label="Top-down actor capture zone">
          <span className="zone-axis zone-axis-x">X</span><span className="zone-axis zone-axis-z">Z</span>
          <span className="zone-centre" />
          {head && <span className="zone-marker zone-head" style={{ left: `${percent(head.x, virtualWidth)}%`, top: `${percent(head.z, virtualDepth)}%` }} title="Head position" />}
          {left && <span className="zone-marker zone-left-hand" style={{ left: `${percent(left.x, virtualWidth)}%`, top: `${percent(left.z, virtualDepth)}%` }} title="Left wrist" />}
          {right && <span className="zone-marker zone-right-hand" style={{ left: `${percent(right.x, virtualWidth)}%`, top: `${percent(right.z, virtualDepth)}%` }} title="Right wrist" />}
        </div>
        <div className="motion-capture-legend"><span>Head</span><span>Left wrist</span><span>Right wrist</span></div>
      </div>
      {outOfBounds && <div className="casting-alert error">Actor has moved outside the configured virtual performance area.</div>}
      <div className="motion-capture-readings">
        <div><small>Head tracking</small><strong>{tracking.head ? "Available" : "Waiting"}</strong></div>
        <div><small>Left hand</small><strong>{tracking.leftWrist ? "Available" : "Not tracked"}</strong></div>
        <div><small>Right hand</small><strong>{tracking.rightWrist ? "Available" : "Not tracked"}</strong></div>
        <div><small>Movement scale X/Z</small><strong>{(virtualWidth / physicalWidth).toFixed(2)}× / {(virtualDepth / physicalDepth).toFixed(2)}×</strong></div>
      </div>
      <p className="muted-note">This first capture step verifies headset and hand-joint telemetry. The next step will bind the calibrated zone to the avatar rig and record timestamped skeletal input. Room-scale movement scaling applies to character root travel only; it must never stretch limb lengths.</p>
    </div>
  </section>;
}
