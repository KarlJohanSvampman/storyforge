# Humanoid pose and rig retargeting

## Canonical source pose

StoryForge capture uses `storyforge.humanoid` v1 in calibrated actor-local metres (Y-up). The capture stream preserves raw Quest head/wrist measurements and stores a reconstructed joint map with separate `tracked` and `inferred` provenance lists.

A take's canonical pose is model-independent. It must not contain target character bone names, bind-pose transforms, mesh scale, or other asset-specific data.

## Retargeting adapter

`frontend/src/humanoidRetargeter.ts` provides `HumanoidRetargeter`.

A `HumanoidRigProfile` maps a rig's bone names to canonical start/end joints. The adapter:
1. Resolves the configured bones in a loaded Three.js hierarchy.
2. Caches their bind-pose local rotations and parent-space segment directions.
3. Optionally applies a uniform character-height fit.
4. Converts canonical joint endpoints into each bone parent's local space.
5. Applies a quaternion correction from the bind direction to the performance direction.

The retargeting preview now uses `detectHumanoidRigProfile` to inspect a loaded skeleton and match common aliases from Mixamo, Blender/Rigify, Unity-style and generic humanoid rigs. It reports mapped and missing semantic segments in the capture workspace. Detection is best-effort: ambiguous or custom rigs should use a hand-authored `HumanoidRigProfile`. The original Mixamo profile remains available as a reference profile.

The motion-capture workspace now resolves the selected cast member's bound character GLB from the project's production asset bindings. If its rig matches the included Mixamo profile, the live/replay canonical pose is applied to that imported model. The procedural preview remains visible when there is no bound model or no compatible mapped bone. This is an initial preview integration, not automatic rig detection or a final production retargeting pipeline.

Example:

```ts
const retargeter = new HumanoidRetargeter(gltf.scene, MIXAMO_HUMANOID_PROFILE, 1.7);
retargeter.apply(canonicalPose);
```

For another rig, provide a profile with that asset's actual bone names and the canonical joints each bone spans. Do not edit the captured take to accommodate a target rig.

## Current limitations

- This first adapter rotates mapped bones but does not yet solve twist distribution, hand/finger articulation, facial animation, root-motion policy, foot locking, or animation blending.
- Height fitting is uniform and approximate; it does not independently normalize limb proportions.
- The GLTF/GLB preview path is wired to project character bindings, but compatibility with real uploaded character assets still requires browser validation.
- Auto-detection is heuristic and name-based; it does not inspect mesh weights or infer bone meaning from geometry. Custom rigs may need hand-authored profiles.
- The inspector currently reports semantic segment coverage but does not yet provide an interactive bone-mapping editor.
- The preview is a capture-workspace validation surface, not yet the full production scene retargeting pipeline.

## Next validation

Upload representative Mixamo, Blender/Rigify and Unity-style humanoid GLB assets. Verify detected bone aliases, mapped/missing segment reports, replay alignment, scale, facing direction, fallback and cleanup. Add interactive profile editing and persistence after validating the heuristic detector on real assets.
