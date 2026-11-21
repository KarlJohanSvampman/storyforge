import { useEffect, useRef, useState } from "react";

type Vec3 = { x: number; y: number; z: number };
type Quaternion = { x: number; y: number; z: number; w: number };
type XRSpaceLike = object;
type XRJointLike = object;
type XRHandLike = { get(name: string): XRJointLike | undefined };
type XRInputSourceLike = { hand?: XRHandLike; handedness?: string };
type XRFrameLike = {
  getViewerPose(space: XRSpaceLike): { transform: { position: Vec3; orientation: Quaternion } } | null;
  getJointPose(joint: XRJointLike, space: XRSpaceLike): { transform: { position: Vec3 } } | null;
};
type XRSessionLike = EventTarget & {
  inputSources: ArrayLike<XRInputSourceLike>;
  requestReferenceSpace(type: string): Promise<XRSpaceLike>;
  requestAnimationFrame(callback: (time: number, frame: XRFrameLike) => void): number;
  end(): Promise<void>;
};
type XRSystemLike = {
  isSessionSupported?(mode: string): Promise<boolean>;
  requestSession(mode: string, options: { requiredFeatures: string[]; optionalFeatures: string[] }): Promise<XRSessionLike>;
};

type TrackingState = {
  head: Vec3 | null;
  leftWrist: Vec3 | null;
  rightWrist: Vec3 | null;
  leftIndex: Vec3 | null;
  rightIndex: Vec3 | null;
  tracking: boolean;
};
type Calibration = { origin: Vec3; yaw: number };
type MappedPoint = { x: number; y: number; z: number };

const EMPTY: TrackingState = {
  head: null, leftWrist: null, rightWrist: null,
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

export default function MotionCaptureSetup({ sceneRunId }: { sceneRunId: string }) {
  const sessionRef = useRef<XRSessionLike | null>(null);
  const referenceSpaceRef = useRef<XRSpaceLike | null>(null);
  const calibrationRef = useRef<Calibration | null>(null);
  const latestRef = useRef<TrackingState>(EMPTY);
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
    try {
      const session = await xr.requestSession("immersive-vr", {
        requiredFeatures: ["local-floor"],
        optionalFeatures: ["hand-tracking"],
      });
      const referenceSpace = await session.requestReferenceSpace("local-floor");
      sessionRef.current = session;
      referenceSpaceRef.current = referenceSpace;
      setStatus("Headset connected · waiting for tracking");
      session.addEventListener("end", () => {
        if (sessionRef.current === session) sessionRef.current = null;
        referenceSpaceRef.current = null;
        latestRef.current = EMPTY;
        setTracking(EMPTY);
        setStatus("Disconnected");
      }, { once: true });

      const tick = (_time: number, frame: XRFrameLike) => {
        if (sessionRef.current !== session) return;
        const space = referenceSpaceRef.current;
        const viewer = space ? frame.getViewerPose(space) : null;
        if (viewer && space) {
          const next: TrackingState = { ...EMPTY, tracking: true, head: viewer.transform.position };
          for (const source of Array.from(session.inputSources)) {
            if (!source.hand) continue;
            const side = source.handedness === "left" ? "left" : source.handedness === "right" ? "right" : null;
            if (!side) continue;
            const wrist = source.hand.get("wrist");
            const index = source.hand.get("index-finger-tip");
            const wristPose = wrist ? frame.getJointPose(wrist, space) : null;
            const indexPose = index ? frame.getJointPose(index, space) : null;
            if (side === "left") {
              next.leftWrist = wristPose?.transform.position || null;
              next.leftIndex = indexPose?.transform.position || null;
            } else {
              next.rightWrist = wristPose?.transform.position || null;
              next.rightIndex = indexPose?.transform.position || null;
            }
          }
          latestRef.current = next;
          setTracking(next);
          setStatus(next.leftWrist || next.rightWrist ? "Head and hand tracking active" : "Head tracking active · enable hand tracking");
        }
        session.requestAnimationFrame(tick);
      };
      session.requestAnimationFrame(tick);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start the WebXR session.");
      setStatus("Connection failed");
    }
  }

  async function disconnect() {
    const session = sessionRef.current;
    sessionRef.current = null;
    referenceSpaceRef.current = null;
    if (session) await session.end().catch(() => undefined);
    latestRef.current = EMPTY;
    setTracking(EMPTY);
    setStatus("Disconnected");
  }

  function calibrate() {
    const head = latestRef.current.head;
    if (!head) { setError("Head tracking has not supplied a pose yet."); return; }
    // The actor's initial headset position defines the zone centre. Its facing direction
    // is captured separately so the square follows the actor's forward orientation.
    const xr = (navigator as Navigator & { xr?: XRSystemLike }).xr;
    const session = sessionRef.current;
    const space = referenceSpaceRef.current;
    if (!xr || !session || !space) return;
    setError("Recenter calibration by reconnecting is not yet supported.");
    setStatus("Calibration origin captured only after facing reference is added.");
  }

  const calibration = calibrationRef.current;
  const head = mapPoint(tracking.head, calibration, physicalWidth, physicalDepth, virtualWidth, virtualDepth);
  const left = mapPoint(tracking.leftWrist, calibration, physicalWidth, physicalDepth, virtualWidth, virtualDepth);
  const right = mapPoint(tracking.rightWrist, calibration, physicalWidth, physicalDepth, virtualWidth, virtualDepth);
  const outOfBounds = calibrated && head && !insideZone(head, virtualWidth, virtualDepth);

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
      <div className="motion-capture-dimensions">
        <label>Physical width (m)<input type="number" min="1" max="8" step="0.1" value={physicalWidth} onChange={event => setPhysicalWidth(Math.max(1, Math.min(8, Number(event.target.value) || 1)))} /></label>
        <label>Physical depth (m)<input type="number" min="1" max="8" step="0.1" value={physicalDepth} onChange={event => setPhysicalDepth(Math.max(1, Math.min(8, Number(event.target.value) || 1)))} /></label>
        <label>Virtual width (m)<input type="number" min="1" max="30" step="0.1" value={virtualWidth} onChange={event => setVirtualWidth(Math.max(1, Math.min(30, Number(event.target.value) || 1)))} /></label>
        <label>Virtual depth (m)<input type="number" min="1" max="30" step="0.1" value={virtualDepth} onChange={event => setVirtualDepth(Math.max(1, Math.min(30, Number(event.target.value) || 1)))} /></label>
      </div>
      <div className="motion-capture-zone">
        <div className="motion-capture-zone-heading"><strong>Actor floor zone</strong><span>{physicalWidth.toFixed(1)} × {physicalDepth.toFixed(1)} m</span></div>
        <div className="motion-capture-zone-map" aria-label="Top-down actor capture zone">
          <span className="zone-axis zone-axis-x">X</span><span className="zone-axis zone-axis-z">Z</span>
          <span className="zone-centre" />
          {head && <span className="zone-marker zone-head" style={{ left: `${percent(head.x, virtualWidth)}%`, top: `${percent(head.z, virtualDepth)}%` }} title="Head position" />}
          {left && <span className="zone-marker zone-left-hand" style={{ left: `${percent(left.x, virtualWidth)}%`, top: `${percent(left.z, virtualDepth)}%` }} title="Left wrist" />}
          {right && <span className="zone-marker zone-right-hand" style={{ left: `${percent(right.x, virtualWidth)}%`, top: `${percent(right.z, virtualDepth)}%` }} title="Right wrist" />}
        </div>
        <div className="motion-capture-legend"><span>Head</span><span>Left wrist</span><span>Right wrist</span></div>
      </div>
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
