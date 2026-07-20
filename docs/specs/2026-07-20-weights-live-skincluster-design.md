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
| `a3obBakedWeights` across the scene | 1.36 MB |
| `a3obBakedWeightsPrevious` across the scene | 1.36 MB |
| Total duplicated weight text | **2.73 MB** |
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

## The workflow this serves

Weights are transferred **from the reference character body, not from the rig**:
`skinCluster1` in the measured scene deforms `Male_bodyShape`, and each garment carries its
own cluster bound to the same joints. The skeleton stays so the result can be posed and
checked.

The two decisions reinforce each other. Transfer produces a live `skinCluster`; testing
weights needs a live rig. There is no point in the workflow at which weights exist without
a cluster to hold them, which is precisely why a second copy has nothing to protect.

**This makes the posed-rig guard load-bearing.** Export reads the deformed mesh, so
exporting while the rig is posed bakes the pose into the model. That was already true, but
a workflow that routinely poses the rig to check weights will meet it often.
`posetest.skeleton_is_posed()` and the `a3obValidate` warning it drives move from a nicety
to a primary safeguard, and must be exercised by the test suite accordingly.

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
  `_add_baked_weight_taggs` entirely.

Added:

- `a3obValidate` warns when a skinned mesh has lost its rig **while a sibling LOD of the
  same model is still skinned**. This is the safety net that replaces the bake: it tells
  the user the moment the situation arises, instead of silently carrying a copy forever
  against a case that should not happen.

### The second trigger was dropped, deliberately

An earlier draft of this section also called for a warning "when a LOD that carries bone
selections has no skinCluster". That was not implemented, and it is not an oversight.

It cannot be implemented honestly. `create_selection_sets` (`import_/builders.py`) turns
**every** Selection TAGG into an ordinary objectSet carrying `a3obSelectionName` — a bone
selection named `Pelvis` and a hidden selection named `camo_jacket` are indistinguishable.
Once the skeleton is gone there is nothing left to match names against, so the check would
either miss real losses or scold the user about camo sets. Making it work would mean adding
a bone-selection marker at import time, which would help only models imported after the
change and would leave every existing scene uncovered.

This is the same reasoning the bake itself rested on: a fresh bind is indistinguishable from
any other rig, so there is no honest heuristic. A scene with no skeleton is likewise
indistinguishable from a static prop. Where there is no signal, this plugin says so rather
than guessing.

### The gap this leaves, stated plainly

Deleting an **entire** skeleton leaves no skinned sibling, so nothing warns — and export is
silent too, because `_warn_about_missing_weights` returns early when the scene holds no
joints. Such an export writes a `.p3d` with zero bone selections. Under the old design the
bake covered this; **this is the one scenario in which this change is strictly worse than
what it replaced.**

It is accepted because it can only occur by violating the premise this whole design rests
on: the skeleton stays in the scene. Partial loss — one garment's rig deleted while its
siblings keep theirs — is the plausible accident, and that is caught. If the workflow ever
changes such that whole skeletons are removed, this decision must be revisited together
with the storage decision above, not patched around.

## Migration — none needed, and why that is safe to assert

The plugin has one user, and every scene at risk was checked rather than assumed. In
`Own_Dreykrus.mb` all six baked meshes carry a live `skinCluster`
(`pants`/`jacket`/`helmet`/`gloves`/`boots`/`backpack` → `skinCluster5`/`2`/`6`/`7`/`4`/`3`),
so no weight exists only as a bake. The removal loses nothing.

Both the write path and the read path go. `a3obBakedWeights` and
`a3obBakedWeightsPrevious` are deleted from the schema, taking
`test_attr_schema.py` from 35 pairs to 33.

That last point is a deliberate edit to a hard contract, so it is recorded here rather
than left to look like drift: the contract exists to stop an attribute silently ceasing to
resolve in scenes that already hold data. Here the data is verified redundant and the
removal is intentional. **Before implementing, re-run the check above** — if any mesh in
any scene has a bake and no live cluster, this section is void and the deprecation dance
comes back.

**The 2.73 MB is not reclaimed by removing the code.** Existing scenes keep both attributes
and their contents indefinitely: nothing reads them, nothing writes them, and re-saving
preserves them like any other dynamic attribute. Only deleting the attributes frees the
space. A small dock action does that, and it is deferred to Phase 3 because it needs the
Preferences window from the Materials spec to have somewhere to live. Until then every
existing scene still carries its full bake — including the measured one.

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

- `weights_survive_skeleton.py` — becomes a test that `a3obValidate` *warns* when a skinned
  mesh has lost its rig. The warning is the replacement safety net, so it needs the same
  coverage the bake had.
- `weight_sync.py` — becomes a test that saving a scene writes no bake.
- `weights_restore.py` — deleted with the `-restore`/`-previous` swap it covers.
- `weights_panel_state.py` — the panel must report the live skinCluster, and must stay a
  silent read (`dock_panel_sync.py` rules still apply).

New:

- Round-trip: bind a garment, export, re-import, and assert the bone selections match the
  live skinCluster within the 1/254 encodable step.
- A scene saved after this change contains no new `a3obBakedWeights` data.

Unchanged gate: `mayapy tests/golden.py verify`. The byte contract does not move — a mesh
with a live skinCluster already exports through `_add_skin_weight_taggs`, which this spec
does not touch.

`tests/python/test_attr_schema.py` **does** move, 35 pairs to 33, and that edit is the
point rather than a side effect. It must be made in the same commit as the attribute
removal, with the reason in the message, so the count never looks like it drifted.

## Open question, deliberately not answered here

Import rebuilds P3D bone selections as selection sets, not as a `skinCluster`. Whether
import should reconstruct a live rig when the skeleton is present is a separate question
from where weights are stored, and is not decided by this spec.
