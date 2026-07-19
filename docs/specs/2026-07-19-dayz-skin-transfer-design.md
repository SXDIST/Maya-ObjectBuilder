# DayZ skin transfer — design

**Date:** 2026-07-19
**Goal:** one action that takes a garment from unrigged to near-final DayZ weights.

## Problem

Binding a garment from scratch requires heavy manual cleanup in four places, all reported by
the user: geometry far from the body (pouches, straps, backpack, helmet peak), joints
(knees/elbows/shoulders), edges and seams, and single stray vertices.

The scene always contains the DayZ reference body (`Male_body`, 111 influences), and every
garment binds to a subset of its joints — measured: no garment uses a joint the body lacks.
So the body already carries correct DayZ weights, including twist and extra bones.

## Approach

Do not recompute weights — **transfer them from the body**. A garment that follows the body's
shape should deform with it; that is also what avoids clipping through it in game.

## Flow

1. **Find the reference.** A mesh with a skinCluster that is not part of the selection. If
   several qualify, the one with the most influences (the body's 111 beats any garment).
   Overridable with an explicit flag.
2. **Bind the target to every joint of the reference.** No guessing which subset is needed —
   unused ones fall out at the pruning step. An existing skinCluster is replaced, since its
   joint set may differ; the whole operation is a single undo step.
3. **Transfer** with `copySkinWeights`, `surfaceAssociation="closestPoint"`,
   `influenceAssociation=["oneToOne", "closestJoint"]`. Same skeleton, so joints match by
   name rather than by geometry.
4. **Rigidify far shells.** Split the target into connected shells (reusing
   `closed_face_islands`). Measure each shell's distance to the body surface with
   `MMeshIntersector`. A shell farther than the threshold gets the *average* of its
   transferred weights applied to all of its vertices, so it moves as one rigid object.
5. **Finish for DayZ:** prune weights below `1/254` (they encode to zero anyway), cap at 4
   influences, normalize.
6. **Report:** vertices processed, shells rigidified, and remaining suspicious vertices via
   the existing `a3obSkinWeights` detector, which also selects them.

## Decisions

- **Distance threshold** — parameter, default `0.03` scene units (garment trousers span ~1.0,
  so ~3 cm). Fitted cloth sits within 1–2 cm; pouches stand off 5–10 cm.
- **Rigid = shell average, not nearest joint.** The average keeps the transition to the body
  smooth (a backpack strap near the shoulder keeps a blend of Spine and shoulder), where a
  single joint would produce a hard jump.
- **The reference body is never modified**, even if it is part of the selection.
- **Not automated: edges and seams.** Maya's own Smooth Skin Weights already covers them, and
  what is "correct" on a cuff is a judgement call — automation can easily make it worse. Add
  later if real cases demand it.

## Verified before design (mayapy)

- `MMeshIntersector` / `MPointOnMesh` exist in API 2.0; `getClosestPoint` returns exact
  distances.
- `cmds.copySkinWeights` and `polyEvaluate(shell=True)` available.
- `closed_face_islands()` already implemented in `commands/helpers/geometry.py`.

## Layout

- `scripts/a3ob/mayabridge/skintransfer.py` — the logic.
- `a3obTransferSkin` command in `commands/skin.py`, alongside the existing detector.
- Dock: new "Skinning" section with the button and the threshold field.

## Testing

`tests/mayapy/skin_transfer.py`:

- a garment-like mesh near a skinned reference gets weights matching the reference at
  corresponding points;
- a shell placed beyond the threshold ends up with identical weights on every one of its
  vertices (rigid), and those weights are not empty;
- output satisfies the DayZ rules: every vertex ≤ 4 influences, sum ≈ 1.0, no weight in
  `(0, 1/254]`;
- the reference mesh's own weights are untouched;
- the whole operation undoes in one step.
