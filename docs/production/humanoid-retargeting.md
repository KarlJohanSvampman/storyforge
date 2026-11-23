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

The included Mixamo profile is a starter mapping, not a guarantee that every Mixamo export has identical naming or hierarchy. Missing mappings are exposed through `missingBones`; callers should surface these to creators rather than silently claiming a complete retarget.

Example:

```ts
const retargeter = new HumanoidRetargeter(gltf.scene, MIXAMO_HUMANOID_PROFILE, 1.7);
retargeter.apply(canonicalPose);
```

For another rig, provide a profile with that asset's actual bone names and the canonical joints each bone spans. Do not edit the captured take to accommodate a target rig.

## Current limitations

- This first adapter rotates mapped bones but does not yet solve twist distribution, hand/finger articulation, facial animation, root-motion policy, foot locking, or animation blending.
- Height fitting is uniform and approximate; it does not independently normalize limb proportions.
- A production character asset has not yet been exercised against this adapter in the browser.
- The current preview is still a procedural avatar. The adapter is the integration seam for subsequent GLTF/GLB character preview and production retargeting.

## Next validation

Load at least two differently proportioned humanoid GLB assets, configure their bone profiles, replay the same take on both, and verify joint alignment, scale, facing direction, missing-bone reporting, and reset behavior before treating the adapter as production-ready.
