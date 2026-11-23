import * as THREE from "three";
import type { CanonicalJointName, CanonicalSkeleton } from "./canonicalSkeleton";

/**
 * Configurable bridge from StoryForge's model-independent pose to a rig's bone names.
 * Each entry identifies a bone at the start joint and its child/end joint.
 */
export type HumanoidBoneBinding = {
  bone: string;
  start: CanonicalJointName;
  end: CanonicalJointName;
};
export type HumanoidRigProfile = {
  id: string;
  label: string;
  bindings: HumanoidBoneBinding[];
  /** Optional approximate target character height in metres, used for uniform fit scaling. */
  targetHeightM?: number;
  /** Defaults to true when targetHeightM is supplied. */
  fitCanonicalHeight?: boolean;
};

type BoundBone = {
  bone: THREE.Bone;
  parent: THREE.Object3D;
  start: CanonicalJointName;
  end: CanonicalJointName;
  restQuaternion: THREE.Quaternion;
  restDirectionInParent: THREE.Vector3;
};

const DEFAULT_CANONICAL_HEIGHT_M = 1.7;

/** Common Mixamo humanoid naming profile; custom profiles support other rigs. */
export const MIXAMO_HUMANOID_PROFILE: HumanoidRigProfile = {
  id: "mixamo-humanoid-v1",
  label: "Mixamo humanoid",
  bindings: [
    { bone: "mixamorigSpine", start: "pelvis", end: "spine" },
    { bone: "mixamorigSpine2", start: "spine", end: "chest" },
    { bone: "mixamorigNeck", start: "chest", end: "neck" },
    { bone: "mixamorigHead", start: "neck", end: "head" },
    { bone: "mixamorigLeftArm", start: "left_shoulder", end: "left_elbow" },
    { bone: "mixamorigLeftForeArm", start: "left_elbow", end: "left_wrist" },
    { bone: "mixamorigRightArm", start: "right_shoulder", end: "right_elbow" },
    { bone: "mixamorigRightForeArm", start: "right_elbow", end: "right_wrist" },
    { bone: "mixamorigLeftUpLeg", start: "left_hip", end: "left_knee" },
    { bone: "mixamorigLeftLeg", start: "left_knee", end: "left_ankle" },
    { bone: "mixamorigRightUpLeg", start: "right_hip", end: "right_knee" },
    { bone: "mixamorigRightLeg", start: "right_knee", end: "right_ankle" },
  ],
};

function jointVector(pose: CanonicalSkeleton, name: CanonicalJointName): THREE.Vector3 | null {
  const point = pose.joints[name];
  return point ? new THREE.Vector3(point.x, point.y, point.z) : null;
}

function worldPointInParent(root: THREE.Object3D, parent: THREE.Object3D, point: THREE.Vector3): THREE.Vector3 {
  return parent.worldToLocal(root.localToWorld(point.clone()));
}

export class HumanoidRetargeter {
  readonly missingBones: string[] = [];
  private readonly root: THREE.Object3D;
  private readonly boundBones: BoundBone[] = [];
  private readonly originalScale: THREE.Vector3;
  private readonly originalPosition: THREE.Vector3;
  private readonly originalQuaternion: THREE.Quaternion;

  constructor(root: THREE.Object3D, profile: HumanoidRigProfile, canonicalHeightM = DEFAULT_CANONICAL_HEIGHT_M) {
    this.root = root;
    this.originalScale = root.scale.clone();
    this.originalPosition = root.position.clone();
    this.originalQuaternion = root.quaternion.clone();
    root.updateMatrixWorld(true);

    for (const binding of profile.bindings) {
      const object = root.getObjectByName(binding.bone);
      if (!(object instanceof THREE.Bone)) {
        this.missingBones.push(binding.bone);
        continue;
      }
      const parent = object.parent;
      if (!parent) {
        this.missingBones.push(binding.bone);
        continue;
      }
      const child = object.children.find(candidate => candidate instanceof THREE.Bone) as THREE.Bone | undefined;
      if (!child) {
        this.missingBones.push(binding.bone);
        continue;
      }
      const boneWorld = new THREE.Vector3();
      const childWorld = new THREE.Vector3();
      object.getWorldPosition(boneWorld);
      child.getWorldPosition(childWorld);
      const restDirectionInParent = parent.worldToLocal(childWorld).sub(parent.worldToLocal(boneWorld)).normalize();
      if (restDirectionInParent.lengthSq() < 1e-8) {
        this.missingBones.push(binding.bone);
        continue;
      }
      this.boundBones.push({
        bone: object,
        parent,
        start: binding.start,
        end: binding.end,
        restQuaternion: object.quaternion.clone(),
        restDirectionInParent,
      });
    }

    if (profile.fitCanonicalHeight !== false && profile.targetHeightM && profile.targetHeightM > 0) {
      const fit = canonicalHeightM / profile.targetHeightM;
      root.scale.copy(this.originalScale).multiplyScalar(fit);
      root.updateMatrixWorld(true);
    }
  }

  get boundBoneCount(): number {
    return this.boundBones.length;
  }

  apply(pose: CanonicalSkeleton): void {
    if (pose.format !== "storyforge.humanoid" || pose.version !== 1 || pose.coordinate_space !== "actor-local-meters") {
      throw new Error("Unsupported canonical skeleton format or coordinate space.");
    }
    this.root.updateMatrixWorld(true);
    for (const binding of this.boundBones) {
      const start = jointVector(pose, binding.start);
      const end = jointVector(pose, binding.end);
      if (!start || !end) continue;
      const startLocal = worldPointInParent(this.root, binding.parent, start);
      const endLocal = worldPointInParent(this.root, binding.parent, end);
      const direction = endLocal.sub(startLocal).normalize();
      if (direction.lengthSq() < 1e-8) continue;
      const correction = new THREE.Quaternion().setFromUnitVectors(binding.restDirectionInParent, direction);
      binding.bone.quaternion.copy(correction.multiply(binding.restQuaternion));
      binding.bone.updateMatrix();
      this.root.updateMatrixWorld(true);
    }
  }

  reset(): void {
    this.root.position.copy(this.originalPosition);
    this.root.quaternion.copy(this.originalQuaternion);
    this.root.scale.copy(this.originalScale);
    for (const binding of this.boundBones) binding.bone.quaternion.copy(binding.restQuaternion);
    this.root.updateMatrixWorld(true);
  }
}
