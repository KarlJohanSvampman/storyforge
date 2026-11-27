import { useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import type { HumanoidBoneBinding, HumanoidRigProfile } from "./humanoidRetargeter";

const SEGMENTS: Array<{ label: string; start: HumanoidBoneBinding["start"]; end: HumanoidBoneBinding["end"] }> = [
  { label: "Spine", start: "pelvis", end: "spine" },
  { label: "Chest", start: "spine", end: "chest" },
  { label: "Neck", start: "chest", end: "neck" },
  { label: "Head", start: "neck", end: "head" },
  { label: "Left upper arm", start: "left_shoulder", end: "left_elbow" },
  { label: "Left forearm", start: "left_elbow", end: "left_wrist" },
  { label: "Right upper arm", start: "right_shoulder", end: "right_elbow" },
  { label: "Right forearm", start: "right_elbow", end: "right_wrist" },
  { label: "Left thigh", start: "left_hip", end: "left_knee" },
  { label: "Left shin", start: "left_knee", end: "left_ankle" },
  { label: "Right thigh", start: "right_hip", end: "right_knee" },
  { label: "Right shin", start: "right_knee", end: "right_ankle" },
];

type Props = {
  profile: HumanoidRigProfile;
  boneNames: string[];
  onChange: (profile: HumanoidRigProfile) => void;
};

export default function HumanoidRigProfileEditor({ profile, boneNames, onChange }: Props) {
  const importRef = useRef<HTMLInputElement>(null);
  const [notice, setNotice] = useState("");
  const counts = useMemo(() => {
    const used = profile.bindings.map(binding => binding.bone).filter(Boolean);
    return { mapped: used.length, duplicates: used.filter((bone, index) => used.indexOf(bone) !== index) };
  }, [profile.bindings]);
  const updateBinding = (start: HumanoidBoneBinding["start"], end: HumanoidBoneBinding["end"], bone: string) => {
    const rest = profile.bindings.filter(binding => binding.start !== start || binding.end !== end);
    onChange({ ...profile, id: "custom-humanoid-v1", label: "Custom humanoid", bindings: bone ? [...rest, { bone, start, end }] : rest });
    setNotice("Profile updated. Changes are stored locally for this character.");
  };
  const exportProfile = () => {
    const blob = new Blob([JSON.stringify({ ...profile, schema: "storyforge.humanoid-rig-profile", version: 1 }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "storyforge-humanoid-rig-profile.json";
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice("Profile exported.");
  };
  const importProfile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as HumanoidRigProfile & { schema?: string; version?: number };
      if (!Array.isArray(parsed.bindings) || parsed.bindings.some(binding =>
        typeof binding.bone !== "string" || !SEGMENTS.some(segment => segment.start === binding.start && segment.end === binding.end)
      )) throw new Error("Invalid rig profile structure.");
      onChange({ id: parsed.id || "custom-humanoid-v1", label: parsed.label || "Imported humanoid", bindings: parsed.bindings, targetHeightM: parsed.targetHeightM, fitCanonicalHeight: parsed.fitCanonicalHeight });
      setNotice("Profile imported and applied.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not import profile.");
    }
    event.target.value = "";
  };

  return <details className="motion-capture-rig-editor">
    <summary>Bone mapping editor · {counts.mapped}/{SEGMENTS.length} mapped</summary>
    <p className="muted-note">Assign each canonical body segment to a bone in this character rig. A selected bone must have a child bone to provide a usable segment direction.</p>
    {counts.duplicates.length > 0 && <p className="production-error">A bone is assigned more than once: {Array.from(new Set(counts.duplicates)).join(", ")}</p>}
    <div className="rig-profile-mapping-list">
      {SEGMENTS.map(segment => {
        const selected = profile.bindings.find(binding => binding.start === segment.start && binding.end === segment.end)?.bone || "";
        return <label key={segment.label}>{segment.label}
          <select value={selected} onChange={event => updateBinding(segment.start, segment.end, event.target.value)}>
            <option value="">Not mapped</option>
            {boneNames.map(name => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>;
      })}
    </div>
    <div className="motion-capture-actions">
      <button type="button" className="secondary-button" onClick={exportProfile}>Export profile</button>
      <button type="button" className="secondary-button" onClick={() => importRef.current?.click()}>Import profile</button>
      <input ref={importRef} type="file" accept="application/json,.json" hidden onChange={event => void importProfile(event)} />
      <span className="muted-note">{notice || "Profiles are saved in this browser, scoped to the selected character."}</span>
    </div>
  </details>;
}
