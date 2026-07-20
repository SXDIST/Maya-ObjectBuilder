# Weights as mesh data — design

**Date:** 2026-07-19
**Status:** SHIPPED. Historical design note — kept for the reasoning, not as a to-do.
Implementation: `mayabridge/weightsync.py` (sync on `kBeforeSave`), `a3obBakedWeights` /
`a3obBakedWeightsPrevious`, `a3obBakeSkin -restore [-previous]`. Covered by
`tests/mayapy/{weight_sync,weights_restore,weights_survive_skeleton}.py`.
**Follows:** the skinning toolkit shipped on `skinning-and-native-cleanup`

## The problem

`.p3d` does not know about skeletons. Weights in the format are named vertex selections —
`LeftFoot`, `Spine1` — with a value per vertex. A file is self-contained: Object Builder opens
it with no rig anywhere.

The plugin made weights **derived from the skeleton**: the truth lives in the `skinCluster`,
which Maya destroys along with the joints. Everything the user complains about follows from
that asymmetry:

- deleting the skeleton loses the weights (patched by `a3obBakeSkin`, but only if remembered);
- transferring weights requires the body to be present in the scene;
- the whole workflow reads as "keep these objects around or things break", which is not how
  Object Builder feels.

The data in the file is self-sufficient; our pipeline is not. That is a property of how we
built it, not of DayZ.

## The goal

Make the mesh the source of truth, exactly as the format has it. The `skinCluster` becomes a
tool for viewing and editing weights, not the place they live. "Is the skeleton in the scene?"
stops being a question.

Alongside that: the plugin should feel like an editor, not a control panel. Work that
*preserves* data happens automatically; work that *changes* it stays an explicit action.
Otherwise convenience becomes the thing that silently ruins a rig — this session was spent
almost entirely on failures of exactly that kind.

## Automation boundary

| Automatic | Explicit |
|---|---|
| syncing weights to the mesh on export | transferring weights from the body (overwrites a rig) |
| loading the reference when one is needed | posing the rig for a test (moves the scene) |
| pruning below 1/254, capping to 4 influences | deleting or replacing a skinCluster |

Rule: **automate what preserves, ask about what overwrites.**

## Stages

Each stage ships independently and is verified before the next. Byte-identical export against
a pre-change baseline is the acceptance test wherever output could change — that check caught
two "improvements" this session that silently altered data.

### 1. Export synchronises weights from the live skin

Before writing, if a mesh has a `skinCluster`, refresh `a3obBakedWeights` from it. Export then
always reads the mesh-side data.

Removes the dependency on the skeleton at export time, and makes `a3obBakeSkin` unnecessary as
a manual step (it stays as a command for explicit use).

*Verify:* delete the skeleton after any edit and export — weights unchanged. Byte-identical
export for a scene whose rig is intact.

### 2. Reference loaded from file, not required in the scene

`a3obTransferSkin` loads the saved reference when the scene has none, uses it, and removes it
again. The body stops being something the user must keep around.

*Verify:* transfer succeeds in a scene containing only the garment and the skeleton; the scene
is left exactly as it was apart from the new weights.

### 3. Import writes weights as mesh data first

Import stores the bone selections on the mesh, and builds a `skinCluster` only when a skeleton
is present. A rigless import becomes fully valid: editable, exportable, weights intact.

*Verify:* import → export without ever creating a skinCluster is byte-identical to the source
file's weight TAGGs.

### 4. UI revision

Remove buttons that stages 1–3 made redundant, and reconsider what remains. Fewer, better
named actions; the dock should not read as a list of workarounds.

### 5. Remaining C++-port habits

Manual scene walks where Maya has a filter, direct writes where a modifier belongs, string
serialisation where a native mechanism exists. Several are already fixed; this is the sweep
for what is left. Not a rewrite — targeted, measured changes only.

## What NOT to do

- **Blind data for vertex flags.** Considered and rejected: 55 vertices in the character
  fixture are referenced by no face, so they do not exist in the Maya mesh at all and cannot
  carry blind data. It would add a second storage mechanism beside the one that must stay.
- **Retyping string attributes into typed arrays.** Measured: parsing is 10-30 ms per LOD and
  the string round-trip is already bit-exact (200k float32 values, zero failures). The win is
  not worth the round-trip risk.
- **Automating seam/edge weights.** Maya's Smooth Skin Weights covers it, and what is
  "correct" on a cuff is a judgement call.

## Method notes for whoever picks this up

- **Measure before optimising.** Every significant find this session came from a profiler or a
  benchmark, never from reading code. The devKit-based audit confidently pointed at bulk APIs
  and promised 10-30x; implementing it made export *slower*, and the real hotspot was
  elsewhere entirely.
- **devKit documents the C++ API.** The 2.0 Python bindings do not cover all of it —
  `MComputation` is in the headers and absent from `maya.api.OpenMaya`. Verify a class exists
  before designing around it.
- **"Native" is not automatically correct.** `MFnSet.getMembers()` is the canonical API call
  and silently drops every face on a set that also holds vertices. `cmds.sets` stays.
- **Run the whole test suite, not the new test.** The `MComputation` breakage surfaced in
  `p3d_workflow`, which had nothing to do with the change being made.
