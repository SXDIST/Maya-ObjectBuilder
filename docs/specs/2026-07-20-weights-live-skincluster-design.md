# Weights: the skinCluster becomes the only source of truth

**Date:** 2026-07-20
**Status:** approved, not implemented
**Reverses:** `docs/specs/2026-07-19-weights-as-mesh-data-design.md` (shipped 2026-07-19)

## Problem

Weights exist twice: in the live `skinCluster`, and as `a3obBakedWeights` — a string
attribute refreshed on every scene save. The second copy exists for one scenario: deleting
a skeleton deletes the skinCluster with it, taking every weight along.

Measured on `Own_Dreykrus.mb` (six garments, 111 joints present, all six skinned):

| Measurement | Value |
|-------------|-------|
| `a3obBakedWeights` across the scene | 1 429 194 characters |
| Per weight entry | 24.3 characters |
| Same data as `uint16` vertex + `uint8` weight | ~180 KB |
| What a weight becomes in the P3D | **one byte**, 1/254 step |
| Live vs baked agreement on `jacket` | 20 318 entries, worst difference **0.0** |
| Influences per vertex (`jacket`) | 1→31, 2→1963, 3→3231, 4→1667 — never above 4 |

The shadow copy is not broken. It is in perfect sync, and redundant: the skeleton is
present, so the data it protects is already in the scene, live.

The cost is not only size. Two representations that can disagree are why
`a3obBakedWeightsPrevious` and the restore-swap exist at all — a fresh bind is
indistinguishable from any other rig, so sync-on-save could overwrite a good bake with a
new bind's defaults, and the only honest defence was to keep the previous copy forever.
Removing the second representation removes that entire class of bug rather than guarding
it.

## This reverses a decision made one day earlier

`2026-07-19-weights-as-mesh-data-design.md` shipped the opposite premise, deliberately:
make the mesh the source of truth, demote the `skinCluster` to a viewing and editing tool,
and stop "is the skeleton in the scene?" from being a question. `a3obBakedWeights` is that
design, not leftover debt.

Its reasoning was sound and is worth stating before overriding it. A `.p3d` is
self-contained — Object Builder opens one with no rig anywhere — while our pipeline was
not, and that asymmetry was ours rather than DayZ's.

What changed is not the reasoning but the premise. The scenario it protects against —
skeleton gone, weights needed — has been ruled out of the workflow: the skeleton always
stays. A self-contained pipeline bought at the cost of 1.43 MB of duplicated text per
scene, plus a second representation that can silently disagree with the first, is not worth
buying for a case that does not occur.

If the workflow ever changes back — garments handed off without a rig, or a scene routinely
stripped of joints — this decision must be revisited, not patched around. The earlier spec
stays in the repository as the record of why the other answer was chosen.

## Decision

**The skeleton always stays in the scene.** The `skinCluster` is then the sole storage:
native, portable inside the single scene file, understood by every Maya weight tool, opens
without the plugin, and costs zero extra bytes.

Rejected alternatives:

- **Sidecar weight files** (`cmds.deformerWeights`). Measured exact and fast — 0.02 s to
  export `jacket`, 0.15 s to import, deviation `5.6e-17` after deliberately scrambling 200
  vertices. Rejected because it breaks the single-file property: copying a `.mb` elsewhere
  leaves the weights behind.
- **A custom weights node.** Rejected outright: the scene must open without the plugin, and
  an unknown node type does not.
- **Colour sets** (RGBA = four weights, a second set = four bone indices). The histogram
  above shows the data fits. Rejected because it is the same custom storage wearing native
  clothing: no Maya tool understands a bone index in a red channel, mesh operations mangle
  colour sets, and it would appear in the artist's Colour Set Editor as garbage.
- **Keeping the bake but encoding it compactly** (~180 KB instead of 1.43 MB). Rejected: it
  shrinks the problem without removing it, and leaves the two-copy bug class in place.

## What changes

Write path removed:

- `weightsync.py` — no longer refreshes a bake on scene save.
- `a3obBakeSkin`'s bake and `-restore -previous` swap.
- Import no longer writes `a3obBakedWeights`.
- `export/taggs/skin.py` keeps `_add_skin_weight_taggs` and drops
  `_add_baked_weight_taggs` from the normal path — see Migration for the timing.

Added:

- `a3obValidate` warns when a skinned mesh has lost its rig, or when a LOD that carries
  bone selections has no skinCluster. This is the safety net that replaces the bake: it
  tells the user the moment the situation arises, instead of silently carrying a copy
  forever against a case that should not happen.

## Migration — the part that must not be rushed

`a3obBakedWeights` and `a3obBakedWeightsPrevious` are entries in the `a3ob*` schema, which
CLAUDE.md names a hard contract, and existing user scenes have both populated. A user whose
skeleton is already gone has nothing but the bake.

Therefore:

1. **The schema entries stay.** They are marked deprecated and read-only. Deleting them
   would be exactly the silent-stop-resolving failure the contract exists to prevent, and
   `test_attr_schema.py`'s 35 pairs stay at 35.
2. **The read path stays** for at least one release: `_add_baked_weight_taggs` still runs
   when a mesh has a bake and no skinCluster, so an already-rigless scene still exports its
   weights.
3. **The write path goes now.** Nothing new is baked; nothing existing is erased.
4. On opening a scene that has a bake but no skinCluster, the dock surfaces a one-time
   "restore the rig from baked weights" action rather than doing it silently.

Only once no supported scene depends on the read path may step 2 be revisited.

## Consequences for the Auto LOD work

`docs/specs/2026-07-20-ui-simplification-design.md` has export generate LODs from a
duplicate of the source. A duplicate has no skinCluster and — once the bake is gone — no
fallback either. The re-bind specified there stops being an optimisation and becomes
required: duplicate → `cmds.skinCluster(influences, dup, toSelectedBones=True)` → copy the
weight array across with `MFnSkinCluster.setWeights`.

That method is measured exact (deviation `0.0`); `cmds.copySkinWeights` is not
(deviation `0.1027` on geometry duplicated from the source, five vertices past the step the
format can encode) and must not be used.

## Testing

The existing mayapy tests name the behaviour being removed and must be rewritten, not
deleted wholesale — each encodes a real failure someone hit:

- `weights_survive_skeleton.py` — becomes a test that `a3obValidate` *warns* when the rig
  is gone, plus that the deprecated read path still exports weights from an existing bake.
- `weight_sync.py` — becomes a test that saving a scene no longer writes a bake, and that
  an existing bake is left untouched rather than erased.
- `weights_restore.py` — keeps the restore-from-bake path under the migration, and drops
  the `-previous` swap.
- `weights_panel_state.py` — the panel must report the live skinCluster, and must stay a
  silent read (`dock_panel_sync.py` rules still apply).

New:

- Round-trip: bind a garment, export, re-import, and assert the bone selections match the
  live skinCluster within the 1/254 encodable step.
- A scene saved after this change contains no new `a3obBakedWeights` data.

Unchanged gates: `mayapy tests/golden.py verify` and `tests/python/test_attr_schema.py`.

## Open question, deliberately not answered here

Import rebuilds P3D bone selections as selection sets, not as a `skinCluster`. Whether
import should reconstruct a live rig when the skeleton is present is a separate question
from where weights are stored, and is not decided by this spec.
