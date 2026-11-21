# Motion Capture and Avateering

> Status: implementation specification and incremental delivery plan. The initial M2.3 UI verifies Quest WebXR tracking and actor-zone calibration; it does not yet record skeletal animation or facial capture.

## Product goal

A director selects a prepared scene, assigns a player to a character, calls Action, and the player performs that character. StoryForge captures a reusable performance that can be refined and replayed independently of the final rendered video.

Body and face are separate animation layers. A body take can be recorded first; a facial performance can be captured later against that body take and synchronized on the same scene-time clock.

## 1. Capture pipeline

1. **Scene preparation:** Scene Builder supplies the environment, cast, props, lights, cameras and scene blocking.
2. **Actor-zone calibration:** Each performer receives a marked physical floor area with a local origin, forward direction, dimensions and tracking profile.
3. **Live body capture:** Quest tracking or another supported tracking source streams timestamped head, hand and (when available) body-joint poses.
4. **Retargeting:** Tracking samples are mapped into a canonical performer skeleton, then retargeted to the cast character's rig.
5. **Body take:** Raw tracking source, calibration snapshot and reconstructed body animation are stored separately.
6. **Facial pass:** A face camera records a close view; face tracking estimates expression channels and maps them to the character's facial rig.
7. **Performance composition:** Body, face, gaze, voice and dialogue tracks are aligned on one timebase and reviewed together.
8. **Refinement:** Directors/animators edit curves, poses, paths, timing, expression keys and transitions without overwriting source captures.

## 2. Actor capture zones

An ActorCaptureZone is a calibrated local coordinate frame on the physical floor. It records:

- physical width and depth in metres
- physical origin on the floor
- actor-facing yaw at calibration
- tracking reference-space identifier and calibration version
- virtual performance width and depth
- root-translation scale on X and Z
- safety inset from the physical boundary
- performer height calibration and optional rig-height ratio
- source device and tracking capabilities

The first setup UI allows physical and virtual dimensions to be entered and captures the current headset position/facing as the zone origin. It shows head and wrist telemetry in a top-down zone diagram.

### Scaling rules

- Default mapping is 1:1.
- Width and depth can have independent root-translation scales when the virtual set requires a different footprint.
- Translation scaling applies to character root travel only. It must not scale bone lengths, hand reach, head size or facial geometry.
- Do not silently warp the actor's skeleton to fit the virtual scene.
- When the planned path exceeds the physical area, use explicit locomotion strategies (walk-in-place, recenter/segment, root-motion, or an approved scale change) and preview the result before recording.
- Boundary warnings are director-visible. Safety margins should stop or warn before the actor reaches the real room boundary.

A zone belongs to a performer/capture session, not to a character permanently. The same performer can be mapped to different character rigs.

## 3. Body capture

### Initial Quest input

The first hardware target is Meta Quest WebXR immersive VR with `local-floor` and optional `hand-tracking` features. Capture:
- viewer/head position and orientation
- left/right wrist pose
- available hand joint poses (initially wrist and index tip for telemetry; expand to full hand joints)
- monotonic sample timestamps
- tracking validity / missing-joint state
- source device and runtime metadata

Quest headset + hand tracking does not provide accurate full-body or leg tracking by itself. Lower-body motion must be explicitly marked as estimated unless a supported additional tracker is connected. Never label inferred legs as captured motion.

### Canonical body representation

Use a rig-independent performer skeleton and normalized local joint transforms where possible. Store source samples and retargeted animation separately. A BodyCaptureSession references the actor zone and device; a BodyAnimationTake references the source session, skeleton definition, calibration snapshot and retargeter version.

### Retargeting and refinement

The runtime preview should initially map head and hand poses to a procedural humanoid rig using inverse kinematics. Shoulder and elbow placement may be inferred and must be identified as inferred. Later passes can add full-body trackers, skeletal reconstruction, foot locking, contact constraints, smoothing and curve editing.

## 4. Facial capture and composition

Facial animation is independent of body animation.

A FaceCaptureSession records a close-up external camera stream and calibration metadata. A face-tracking adapter estimates facial channels. The initial facial rig target should support:
- left/right brow raise and lower
- blink and eye openness
- eye gaze
- cheek raise
- smile/frown
- jaw open
- lip shapes / visemes
- mouth corner and lip compression

An ordinary webcam does not guarantee high-quality facial capture. Camera quality, lighting, frame rate, face visibility, tracking software and calibration affect results. Store the source video privately with explicit access controls; store extracted facial curves as a separate animation asset. Face capture requires clear performer consent and must not imply identity or voice cloning.

### Performance Composer

A composition contains independently editable tracks:
- body animation
- facial expression animation
- eye gaze
- dialogue / voice
- optional gesture or prop interaction tracks

The facial pass can be recorded after the body pass by playing back the body take as a reference. Both use a shared scene-time clock and explicit sync offset. A replacement facial take must not alter the body take. A replacement body take must not delete facial work; the composer should flag alignment for review.

## 5. Recording and provenance

High-frequency samples must not be written as one relational-database row per frame. Use chunked capture payloads or object storage for raw streams and animation curves; relational records hold session metadata, checksums, versions and references.

Every take records:
- scene run and cast-member instance
- actor/capture-zone snapshot
- source device and tracking capabilities
- start/end timestamps and timebase
- raw capture asset reference and checksum
- reconstructed body/face asset references and checksums
- skeleton and facial-rig versions
- retargeter / tracker version
- missing tracking intervals and inferred channels
- editor revisions and provenance links

Raw captures are immutable. Corrections create new animation revisions. Final performance composition is non-destructive and remains distinct from the camera footage and editorial EDL.

## 6. Delivery milestones

### M2.3.1 — Capture setup and calibration
- [x] Add a director-side Quest WebXR connection and tracking telemetry panel.
- [x] Configure physical and virtual actor-zone dimensions.
- [x] Calibrate actor-zone origin and facing direction from the current headset pose.
- [x] Display head/wrist positions in a top-down zone view and warn when the mapped head leaves the virtual boundary.
- [ ] Persist calibration profiles and snapshots to the backend.
- [ ] Test on a physical Quest headset/browser.

### M2.3.2 — Live avateering
- [ ] Add a humanoid skeletal preview rig.
- [ ] Map headset pose and hand joints to the rig using inverse kinematics.
- [ ] Apply actor-zone root mapping without changing limb proportions.
- [ ] Show missing tracking and inferred joints explicitly.
- [ ] Add calibration/recenter and safe boundary feedback.

### M2.3.3 — Body take capture
- [ ] Add a timestamped high-frequency input stream and chunked storage.
- [ ] Record raw samples and retargeted body animation as separate assets.
- [ ] Add Action/Cut controls and take finalization.
- [ ] Replay skeletal animation and preserve source provenance.

### M2.3.4 — Body refinement
- [ ] Edit body actions, poses, root path, timing, curves and transitions.
- [ ] Preserve source take and save non-destructive animation revisions.
- [ ] Compare planned blocking with captured performance.

### M2.3.5 — Facial capture
- [ ] Add external-camera permission and device selection.
- [ ] Add neutral-face calibration and face tracking adapter.
- [ ] Map tracked expressions to blendshape/morph-target channels.
- [ ] Save a separate facial take with source-video provenance and consent controls.

### M2.3.6 — Performance Composer
- [ ] Align facial take to a recorded body take.
- [ ] Add separate body, face, gaze and dialogue tracks.
- [ ] Edit facial curves and expression keyframes independently.
- [ ] Preview the combined character performance.
- [ ] Export a composed animation reference for scene playback and rendering.

### Later
- Multi-performer network capture, additional body trackers, foot/contact solving, advanced facial capture, lip-sync refinement, and cross-rig retargeting.

## 7. First acceptance test

On a Quest headset, a performer can connect to a prepared scene, calibrate a marked floor zone, move their head and hands, and see stable tracked positions relative to the calibrated zone. The director can identify tracking availability and boundary excursions. No claim of full-body capture is made until skeletal reconstruction and additional tracking are implemented.
