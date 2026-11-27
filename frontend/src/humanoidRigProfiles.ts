import * as THREE from "three";
import type { HumanoidBoneBinding, HumanoidRigProfile } from "./humanoidRetargeter";

type SemanticBinding = {
  key: string;
  start: HumanoidBoneBinding["start"];
  end: HumanoidBoneBinding["end"];
  aliases: string[];
};

const SEMANTIC_BINDINGS: SemanticBinding[] = [
  { key: "spine", start: "pelvis", end: "spine", aliases: ["spine", "spine01", "spine1", "spine_lower", "spinea"] },
  { key: "chest", start: "spine", end: "chest", aliases: ["spine2", "spine02", "spine001", "spine002", "spine_upper", "spineb", "chest", "upperchest"] },
  { key: "neck", start: "chest", end: "neck", aliases: ["neck", "neck1"] },
  { key: "head", start: "neck", end: "head", aliases: ["head", "headbone"] },
  { key: "leftUpperArm", start: "left_shoulder", end: "left_elbow", aliases: ["leftarm", "leftupperarm", "upperarml", "upperarmleft", "arml", "upperlimb_l"] },
  { key: "leftForearm", start: "left_elbow", end: "left_wrist", aliases: ["leftforearm", "leftlowerarm", "forearml", "lowerarml", "forearmleft", "lowerarmleft", "armlowerl"] },
  { key: "rightUpperArm", start: "right_shoulder", end: "right_elbow", aliases: ["rightarm", "rightupperarm", "upperarmr", "upperarmright", "armr", "upperlimb_r"] },
  { key: "rightForearm", start: "right_elbow", end: "right_wrist", aliases: ["rightforearm", "rightlowerarm", "forearmr", "lowerarmr", "forearmright", "lowerarmright"] },
  { key: "leftThigh", start: "left_hip", end: "left_knee", aliases: ["leftupleg", "leftupperleg", "thighl", "upperlegl", "thighleft", "upperlegleft", "legupperl"] },
  { key: "leftShin", start: "left_knee", end: "left_ankle", aliases: ["leftleg", "leftlowerleg", "calfl", "shinl", "lowerlegl", "calfleft", "shinleft", "leglowerl"] },
  { key: "rightThigh", start: "right_hip", end: "right_knee", aliases: ["rightupleg", "rightupperleg", "thighr", "upperlegr", "thighright", "upperlegright", "legupperr"] },
  { key: "rightShin", start: "right_knee", end: "right_ankle", aliases: ["rightleg", "rightlowerleg", "calfr", "shinr", "lowerlegr", "calfright", "shinright", "leglowerr"] },
];

export type HumanoidRigDetection = {
  profile: HumanoidRigProfile;
  matchedSegments: string[];
  missingSegments: string[];
  boneNames: string[];
};

export type HumanoidRigPreviewStatus = {
  message: string;
  boneNames: string[];
  matchedSegments: string[];
  missingSegments: string[];
};

export function normalizeHumanoidBoneName(name: string): string {
  const leaf = name.split(/[|:]/).pop() || name;
  return leaf
    .replace(/^mixamorig/i, "")
    .replace(/^(armature|def|org|mch)[-_]?/i, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

/**
 * Best-effort semantic mapping for common Mixamo, Blender/Rigify, Unity and
 * Unreal-style humanoid bone names. The result is always inspectable and can
 * be replaced by a hand-authored profile when a rig uses unusual naming.
 */
export function detectHumanoidRigProfile(root: THREE.Object3D): HumanoidRigDetection {
  const bones: THREE.Bone[] = [];
  root.traverse(object => {
    if (object instanceof THREE.Bone) bones.push(object);
  });
  const byName = new Map<string, THREE.Bone[]>();
  for (const bone of bones) {
    const normalized = normalizeHumanoidBoneName(bone.name);
    const matches = byName.get(normalized) || [];
    matches.push(bone);
    byName.set(normalized, matches);
  }

  const bindings: HumanoidBoneBinding[] = [];
  const matchedSegments: string[] = [];
  const missingSegments: string[] = [];
  const used = new Set<THREE.Bone>();
  for (const semantic of SEMANTIC_BINDINGS) {
    const candidates = semantic.aliases
      .map(alias => byName.get(normalizeHumanoidBoneName(alias)) || [])
      .flat();
    const bone = candidates.find(candidate => !used.has(candidate));
    if (!bone) {
      missingSegments.push(semantic.key);
      continue;
    }
    used.add(bone);
    bindings.push({ bone: bone.name, start: semantic.start, end: semantic.end });
    matchedSegments.push(semantic.key);
  }

  const family = bones.some(bone => /mixamorig/i.test(bone.name))
    ? "Mixamo-compatible"
    : bones.some(bone => /[._](l|r)$/i.test(bone.name) || /^(DEF|ORG|MCH)[-_]/i.test(bone.name))
      ? "Blender/Rigify-style"
      : bones.some(bone => /^(Left|Right)(UpperArm|LowerArm|UpperLeg|LowerLeg)/i.test(bone.name))
        ? "Unity-style"
        : "Generic humanoid";
  return {
    profile: {
      id: "autodetected-humanoid-v1",
      label: family,
      bindings,
      fitCanonicalHeight: true,
    },
    matchedSegments,
    missingSegments,
    boneNames: bones.map(bone => bone.name).sort((a, b) => a.localeCompare(b)),
  };
}
