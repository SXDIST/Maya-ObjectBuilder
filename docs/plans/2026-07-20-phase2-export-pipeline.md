# Phase 2: the export pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto LOD becomes an export option instead of a dock panel, texture import becomes
optional, and validation runs on every export with a severity tier that can actually stop a
bad file being written.

**Architecture:** Three specs land together because all three edit `translator.py`'s
`do_read`/`do_write` and `scripts/mayaObjectBuilderP3DOptions.mel`. Splitting them would mean
three sequential conflicting edits to the same two files. Structural moves come first so the
behaviour changes have somewhere to live.

**Tech Stack:** Python 3, Maya API 2.0 (`maya.api.OpenMaya`, `OpenMayaAnim`), API 1.0 for the
translator shell, MEL for the option box, `mayapy` for Maya tests, plain CPython for the rest.

**Specs:** `docs/specs/2026-07-20-ui-simplification-design.md` (Auto LOD, texture import),
`docs/specs/2026-07-20-validation-at-export-design.md`

## Global Constraints

- **Never run `mayapy tests/golden.py capture`.** It overwrites the byte-gate baseline from
  current behaviour, after which the gate approves anything. `verify` only — even when a
  skip message suggests otherwise.
- The byte gate must stay at `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.
  **Auto LOD defaults to off, so a default export must produce identical bytes.** If the
  gate moves, something changed that should not have.
- `mayapy` is `C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe`. Each mayapy test runs in
  its own process — `maya.standalone` cannot be initialised twice.
- **Run every command in the FOREGROUND.** Two implementer agents in Phase 1 stalled waiting
  on background suite runs. The suite takes several minutes; that is normal.
- A registered `MPxCommand` ignores code changes on plugin reload — the class keeps the
  session's first version. Verify command changes under `mayapy`, not interactive Maya.
- Mixed line endings, no `.gitattributes`. Targeted edits only; check `git diff --shortstat`
  against `--ignore-cr-at-eol` before committing.
- `MSyntax.addFlag` takes ONE argument type per flag, and the long names `set` and `fix` are
  reserved — a bad flag raises "Unexpected Internal Failure" from a C++ callback that cannot
  absorb a Python exception, killing the session with unsaved work.
- Layering: `formats` → `mayabridge` → `ui`. `mayabridge` must never import from `a3ob.ui`.
  Task 1 exists to keep that true.
- `tests/mayapy/*.py` are auto-discovered by `tests/run_all.py` EXCEPT files starting with
  `_`; they use `_harness.bootstrap()` / `_harness.check(cond, msg)` / `_harness.REPO`.
- Suite is currently 41/41. Keep it there.

## Prerequisite

`Arma3ObjectBuilder-master/` and `build/golden/` are junction-linked into this worktree from
the main repo (both are gitignored, so `git worktree add` did not bring them). Confirm before
starting — without them `golden.py verify` prints SKIP and every byte assertion is vacuous:

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```
Expected: real per-fixture lines, not `SKIP`.

## File Structure

| File | Responsibility after this phase |
|------|-------------------------------|
| `scripts/a3ob/mayabridge/autolod/` | the generator, moved out of `ui/` so export may call it |
| `scripts/a3ob/mayabridge/undoctl.py` | undo suspension, shared by both layers |
| `scripts/a3ob/mayabridge/translator.py` | reads options, runs validation, drives Auto LOD |
| `scripts/mayaObjectBuilderP3DOptions.mel` | gains the Auto LOD frame and the texture toggle |
| `scripts/a3ob/mayabridge/commands/validate.py` | three severities; scene-global checks hoisted |
| `scripts/a3ob/ui/dock.py`, `panels/lod.py` | no Auto LOD section |

---

### Task 1: Move `autolod` into `mayabridge`

Pure relocation. Nothing inside the package changes — it already imports only from itself,
`maya.cmds` and `maya.api.OpenMaya`, which is why this is safe.

**Files:**
- Move: `scripts/a3ob/ui/autolod/` → `scripts/a3ob/mayabridge/autolod/`
- Modify: `scripts/objectBuilderAutoLOD.py` (external facade — CLAUDE.md says keep it)
- Modify: `scripts/a3ob/ui/actions/lod.py` (`_auto_lod_module`)
- Modify: `tests/mayapy/autolod_cancel_leaves_no_debris.py`,
  `tests/mayapy/autolod_properties.py`, `tests/python/test_qem.py`
- Modify: `CLAUDE.md` — the architecture paragraph lists `autolod/` under `a3ob/ui/`

**Interfaces:**
- Produces: `from a3ob.mayabridge.autolod import generate_auto_lods` — same signature,
  `generate_auto_lods(settings=None) -> list[str]`.

- [ ] **Step 1: Move it**

```bash
git mv scripts/a3ob/ui/autolod scripts/a3ob/mayabridge/autolod
```

- [ ] **Step 2: Rewrite the internal import paths**

Every module inside the package imports itself by absolute path. Update all of them:

```bash
grep -rln "a3ob\.ui\.autolod" scripts/ tests/
```

Replace `a3ob.ui.autolod` with `a3ob.mayabridge.autolod` in every hit. Read each file after
editing — a `from X import *` whose module moved fails at import, not at call.

- [ ] **Step 3: Verify nothing still points at the old path**

```bash
grep -rn "ui\.autolod\|ui/autolod" scripts/ tests/ plug-ins/ docs/ --include=*.py --include=*.md
```
Expected: hits only in `docs/` prose describing history. Any hit in `scripts/`, `tests/` or
`plug-ins/` is a live break.

- [ ] **Step 4: Run the tests that cover it**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_properties.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_cancel_leaves_no_debris.py
python -m pytest tests/python/test_qem.py -v
python tests/run_all.py
```
Expected: all pass, suite 41/41.

- [ ] **Step 5: Update CLAUDE.md's architecture paragraph**

It currently lists `autolod/` among `a3ob/ui/`'s contents. Move it to the `mayabridge`
sentence. Do not restructure the paragraph — one term moves.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: move autolod into mayabridge

Export lives in mayabridge and is about to drive LOD generation, and mayabridge
must never import from a3ob.ui. The package was already self-contained — it
imported only from itself and Maya — so this is a relocation, not an untangling."
```

---

### Task 2: Move undo suspension into `mayabridge`

**Files:**
- Create: `scripts/a3ob/mayabridge/undoctl.py`
- Modify: `scripts/a3ob/ui/_undo.py` — re-export, so no caller changes

**Interfaces:**
- Produces: `undo_suspended()` and `undo_chunk(name)` context managers in
  `a3ob.mayabridge.undoctl`; `a3ob.ui._undo` re-exports both under their existing names
  `_undo_suspended` / `_undo_chunk`.

- [ ] **Step 1: Create the leaf**

Move the two context managers out of `scripts/a3ob/ui/_undo.py` verbatim, keeping their
docstrings — the `_undo_suspended` one records that restoring the prior state (rather than
forcing undo back on) is what fixed a bug that left Maya's undo queue dead for a whole
session. Name them `undo_chunk` and `undo_suspended` in the new module.

- [ ] **Step 2: Re-export from the old home**

`scripts/a3ob/ui/_undo.py` becomes:

```python
"""Undo-queue context managers.

The implementations live in ``a3ob.mayabridge.undoctl`` so the export path can use them
without mayabridge importing from a3ob.ui. This module stays as the name every UI caller
already imports.
"""

from a3ob.mayabridge.undoctl import undo_chunk as _undo_chunk
from a3ob.mayabridge.undoctl import undo_suspended as _undo_suspended

__all__ = ["_undo_chunk", "_undo_suspended"]
```

- [ ] **Step 3: Verify no caller changed**

```bash
grep -rn "_undo_chunk\|_undo_suspended" scripts/ tests/ --include=*.py
```
Every hit outside these two files should be an unchanged import from `a3ob.ui._undo`.

- [ ] **Step 4: Run the undo tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_undo.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/undo_survives_dock_actions.py
python tests/run_all.py
```
Expected: pass, 41/41.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: move undo suspension to a mayabridge leaf

The export path needs it and mayabridge must not import from a3ob.ui.
ui/_undo.py re-exports, so no caller changes."
```

---

### Task 3: Make the generator non-consuming

The heart of the phase. `_generate_resolution_lods` currently does
`duplicate = cmds.rename(source, name)` for index 0 — it **consumes** the user's mesh into
LOD1. Transient generation is impossible while that stands, because the source is one of the
nodes that would be deleted afterwards.

**Files:**
- Modify: `scripts/a3ob/mayabridge/autolod/lodgen.py`
- Create: `tests/mayapy/autolod_does_not_consume_source.py`

**Interfaces:**
- Consumes: `generate_auto_lods` from Task 1's new location.
- Produces: `_generate_resolution_lods(source, settings, visuals)` — unchanged signature; the
  source node survives with its name, parent, skinCluster and set membership intact.

- [ ] **Step 1: Write the failing test**

```python
"""Auto LOD leaves the source mesh alone (run with mayapy).

_generate_resolution_lods used to rename the source into LOD1 — it consumed the mesh
the user selected. Generation at export has to be able to delete everything it made,
which is impossible while one of those nodes is the user's own mesh.

Run:  mayapy.exe tests/mayapy/autolod_does_not_consume_source.py
"""

import os

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_skinned_source():
    cmds.file(new=True, force=True)
    transform = cmds.polySphere(name="garment", r=1, sx=12, sy=12, ch=False)[0]
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -1, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 1, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)
    # A selection set on the source: generation must carry it onto LOD1, not lose it.
    cmds.select(transform + ".vtx[0:10]", replace=True)
    set_node = cmds.sets(name="a3ob_SEL_camo_test")
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", "camo_test", type="string")
    cmds.select(transform, replace=True)
    return transform


def live_weights(mesh):
    shape = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True)[0]
    skins = cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")
    if not skins:
        return None
    sel = om.MSelectionList(); sel.add(skins[0])
    fn = oma.MFnSkinCluster(sel.getDependNode(0))
    sel2 = om.MSelectionList(); sel2.add(shape)
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(cmds.polyEvaluate(mesh, vertex=True))
    weights, _cols = fn.getWeights(sel2.getDagPath(0), comp)
    return list(weights)


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    from a3ob.mayabridge.autolod import generate_auto_lods

    source = build_skinned_source()
    before = live_weights(source)
    _harness.check(before is not None, "fixture must be skinned or this test proves nothing")

    generated = generate_auto_lods({"resolution": True, "geometry": False})
    _harness.check(bool(generated), "expected generated LODs, got %r" % (generated,))

    _harness.check(cmds.objExists(source),
                   "the source mesh must survive generation under its own name")
    after = live_weights(source)
    _harness.check(after is not None,
                   "the source must keep its skinCluster")
    _harness.check(after == before,
                   "the source's weights must be untouched")

    # LOD1 is a copy now, so it must have been given the source's weights and selections.
    lod1 = [n for n in generated if cmds.objExists(n)
            and "1" in n.split("|")[-1] and n.split("|")[-1] != source]
    _harness.check(bool(lod1), "expected a full-resolution LOD, got %r" % (generated,))
    lod1_weights = live_weights(lod1[0])
    _harness.check(lod1_weights is not None,
                   "LOD1 must be bound — a duplicate has no skinCluster unless re-bound")
    _harness.check(max(abs(a - b) for a, b in zip(before, lod1_weights)) == 0.0,
                   "LOD1's weights must match the source EXACTLY; copySkinWeights is not "
                   "exact enough (measured 0.1027 on identical geometry)")
    members = cmds.sets("a3ob_SEL_camo_test", query=True) or []
    _harness.check(any(lod1[0].split("|")[-1] in m for m in members),
                   "LOD1 must have been added to the source's selection set, got %r" % (members,))
    print("OK - source survives intact, LOD1 carries its weights and selections")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_does_not_consume_source.py`
Expected: FAIL — `the source mesh must survive generation under its own name`

- [ ] **Step 3: Replace the rename with a duplicate**

In `scripts/a3ob/mayabridge/autolod/lodgen.py`, `_generate_resolution_lods` currently has:

```python
        if index == 0:
            # Keep the rename result as a short name (like the duplicate branch below).
            # ...
            duplicate = cmds.rename(source, name)
        else:
            duplicate = cmds.duplicate(source_snapshot, name=name, returnRootsOnly=True)[0]
```

Index 0 becomes a duplicate like every other index, and then gets what the rename used to
give it for free — the source's selections and its rig:

```python
        duplicate = cmds.duplicate(source_snapshot, name=name, returnRootsOnly=True)[0]
        if index == 0:
            # LOD1 used to BE the source (cmds.rename), which is why it needed nothing here.
            # It is a copy now, so the two things the rename gave it for free have to be
            # given explicitly: the source's selection sets, and its rig.
            _propagate_named_selections(source, duplicate, full_resolution=True)
            _rebind_like(source, duplicate)
```

- [ ] **Step 4: Write the exact re-bind**

Add to `lodgen.py`. **The method matters and is measured** — do not substitute
`cmds.copySkinWeights`:

```python
def _rebind_like(source, target):
    """Bind ``target`` to ``source``'s influences and copy the weight array verbatim.

    ``target`` is a duplicate of ``source``, so vertex order is identical and index i maps
    to index i — no surface association is needed, and none may be used. Measured on a real
    garment (6892 verts, 25 influences): writing the array through
    ``MFnSkinCluster.setWeights`` deviates by 0.0, while ``cmds.copySkinWeights`` with
    closestPoint/oneToOne deviates by 0.1027 on that same identical geometry, putting five
    vertices past the 1/254 step the P3D format can even encode. Coincident points make the
    association pick arbitrarily; there is nothing to tune."""
    import maya.api.OpenMayaAnim as oma

    source_shape = cmds.listRelatives(source, shapes=True, noIntermediate=True, fullPath=True)
    if not source_shape:
        return None
    source_skin = cmds.ls(cmds.listHistory(source_shape[0], pruneDagObjects=True) or [],
                          type="skinCluster")
    if not source_skin:
        return None  # unrigged source: nothing to carry across

    influences = cmds.skinCluster(source_skin[0], query=True, influence=True) or []
    if not influences:
        return None

    def _fn_and_component(mesh):
        shape = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True)[0]
        skins = cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")
        selection = om.MSelectionList()
        selection.add(skins[0])
        fn = oma.MFnSkinCluster(selection.getDependNode(0))
        paths = om.MSelectionList()
        paths.add(shape)
        component = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
        om.MFnSingleIndexedComponent(component).setCompleteData(
            cmds.polyEvaluate(mesh, vertex=True))
        return fn, paths.getDagPath(0), component

    source_fn, source_path, source_component = _fn_and_component(source)
    weights, influence_count = source_fn.getWeights(source_path, source_component)

    cmds.skinCluster(influences, target, toSelectedBones=True, bindMethod=0,
                     skinMethod=0, normalizeWeights=1)
    target_fn, target_path, target_component = _fn_and_component(target)
    target_fn.setWeights(target_path, target_component,
                         om.MIntArray(range(influence_count)), weights, False)
    return target
```

`lodgen.py` already imports `maya.cmds as cmds`; add `import maya.api.OpenMaya as om` at the
top if it is not there.

- [ ] **Step 5: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_does_not_consume_source.py`
Expected: `OK - source survives intact, LOD1 carries its weights and selections`

- [ ] **Step 6: Check what the source snapshot is now for**

`_generate_resolution_lods` takes `source_snapshot = cmds.duplicate(source, ...)` at the top
and `cmds.delete(source_snapshot)` at the end. With index 0 no longer consuming `source`,
read whether the snapshot is still needed or whether `source` can be duplicated directly. If
it is now redundant, remove it — but only if you can say why it was there. It exists because
the rename destroyed the original; that reason is gone.

- [ ] **Step 7: Run the autolod suite**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_properties.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_cancel_leaves_no_debris.py
python tests/run_all.py
```
Expected: pass, 41/41. `autolod_cancel_leaves_no_debris.py` matters most here — cancelling
must still leave the scene untouched, and the cleanup path now has one more node shape to
consider.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: stop Auto LOD consuming the mesh it generates from

_generate_resolution_lods renamed the source into LOD1. Generation at export
has to be able to delete everything it made, and it cannot while one of those
nodes is the user's own mesh.

LOD1 is a duplicate now, so it is given explicitly what the rename gave it for
free: the source's selection sets, and its rig. The rig is copied by writing
the weight array through MFnSkinCluster.setWeights — measured at 0.0 deviation
on a real garment, against 0.1027 for cmds.copySkinWeights on that same
identical geometry, which puts five vertices past the step the format can
encode."
```

---

### Task 4: Auto LOD options in the option box

**Files:**
- Modify: `scripts/mayaObjectBuilderP3DOptions.mel`
- Create: `tests/python/test_autolod_options.py`

**Interfaces:**
- Produces: option-string keys `autoLod`, `autoLodOutput`, `autoLodReduction`,
  `autoLodFirst`, `autoLodResolution`, `autoLodGeometry`, `autoLodMemory`, `autoLodFire`,
  `autoLodView`, `autoLodGeometryType`, `autoLodFireQuality`. Task 5 parses them.

- [ ] **Step 1: Write the failing test**

`translator.parse_options` is Maya-free, so this runs under plain CPython. Read
`tests/python/test_attr_schema.py` for how this suite reads a source file with `ast` rather
than importing it — `translator.py` imports Maya at module level, so **import it the same
way or read it as text**; do not `import a3ob.mayabridge.translator`.

```python
"""The Auto LOD option keys parse with the documented defaults.

The option box hands the translator a "key=value;key=value" string. These keys are new;
their defaults decide what a user who never opens the option box gets, and the answer
has to be "exactly what happened before".
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEL = ROOT / "scripts" / "mayaObjectBuilderP3DOptions.mel"

AUTOLOD_KEYS = [
    "autoLod", "autoLodOutput", "autoLodReduction", "autoLodFirst",
    "autoLodResolution", "autoLodGeometry", "autoLodMemory", "autoLodFire",
    "autoLodView", "autoLodGeometryType", "autoLodFireQuality",
]


def test_every_autolod_key_is_emitted():
    text = MEL.read_text(encoding="utf-8", errors="ignore")
    missing = [key for key in AUTOLOD_KEYS if '"%s"' % key not in text]
    assert not missing, "option string never emits: %r" % (missing,)


def test_autolod_is_off_by_default():
    text = MEL.read_text(encoding="utf-8", errors="ignore")
    line = [ln for ln in text.splitlines() if '"autoLod"' in ln and "Default" in ln]
    assert line, "autoLod has no default-bearing emit line"
    assert '"0"' in line[0], (
        "autoLod must default to 0 — a default export must not silently generate LODs: %r"
        % (line[0],))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/python/test_autolod_options.py -v`
Expected: FAIL — `option string never emits: ['autoLod', ...]`

- [ ] **Step 3: Add the frame**

In `mayaObjectBuilderP3DOptions.mel`, inside the `else` branch (the export half), after the
existing `LODs` frame, add a collapsed frame. Follow the file's existing style exactly —
`frameLayout` + `columnLayout` + controls, and `setParent ".."` twice:

```mel
            frameLayout -label "Auto LOD (generated on export)" -collapsable true -collapse true -marginWidth 8 -marginHeight 6;
            columnLayout -adjustableColumn true -rowSpacing 4;
            checkBox -label "Generate LODs on export" mayaObjectBuilderAutoLod;
            optionMenu -label "Output" mayaObjectBuilderAutoLodOutput;
            menuItem -label "Quads";
            menuItem -label "Triangles";
            optionMenu -label "Reduction" mayaObjectBuilderAutoLodReduction;
            menuItem -label "Aggressive";
            menuItem -label "Balanced";
            menuItem -label "Light";
            optionMenu -label "First LOD" mayaObjectBuilderAutoLodFirst;
            menuItem -label "LOD1";
            menuItem -label "LOD0";
            checkBox -label "Resolution LODs" mayaObjectBuilderAutoLodResolution;
            checkBox -label "Geometry LOD" mayaObjectBuilderAutoLodGeometry;
            checkBox -label "Memory LOD" mayaObjectBuilderAutoLodMemory;
            checkBox -label "Fire Geometry LOD" mayaObjectBuilderAutoLodFire;
            checkBox -label "View Geometry LOD" mayaObjectBuilderAutoLodView;
            optionMenu -label "Geometry" mayaObjectBuilderAutoLodGeometryType;
            menuItem -label "BOX";
            menuItem -label "NONE";
            intSliderGrp -label "Fire quality" -field true -minValue 1 -maxValue 10 -value 2 mayaObjectBuilderAutoLodFireQuality;
            setParent "..";
            setParent "..";
```

- [ ] **Step 4: Wire set and get**

Add to `mayaObjectBuilderP3DSetOptions` one `else if` per key, matching the file's existing
pattern (`mayaObjectBuilderP3DSetBool` / `SetMenu`). The menu values need entries in both
`mayaObjectBuilderP3DMenuLabelToValue` and `mayaObjectBuilderP3DMenuValueToLabel`:
`Quads`/`quads`, `Triangles`/`triangles`, `Aggressive`/`aggressive`, `Balanced`/`balanced`,
`Light`/`light`, `LOD1`/`LOD1`, `LOD0`/`LOD0`, `BOX`/`BOX`, `NONE`/`NONE`.

Add to `mayaObjectBuilderP3DGetOptions` one line per key with these defaults:

| Key | Default |
|-----|---------|
| `autoLod` | `"0"` |
| `autoLodOutput` | `quads` |
| `autoLodReduction` | `aggressive` |
| `autoLodFirst` | `LOD1` |
| `autoLodResolution` | `"1"` |
| `autoLodGeometry` | `"1"` |
| `autoLodMemory` | `"0"` |
| `autoLodFire` | `"0"` |
| `autoLodView` | `"0"` |
| `autoLodGeometryType` | `BOX` |
| `autoLodFireQuality` | `2` |

`autoLodFireQuality` is an integer, not a bool or a menu — the file has no helper for that.
Add one following the shape of `mayaObjectBuilderP3DBoolOptionDefault`, reading with
`intSliderGrp -query -value`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/python/test_autolod_options.py -v`
Expected: PASS

- [ ] **Step 6: Verify the option box still builds in Maya**

MEL syntax errors do not surface in a text test. Open the dialog under mayapy:

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import maya.mel as mel, maya.cmds as cmds; cmds.loadPlugin('plug-ins/MayaObjectBuilder.py'); mel.eval('source \"scripts/mayaObjectBuilderP3DOptions.mel\"'); print(mel.eval('mayaObjectBuilderP3DGetOptions()'))"
```
Expected: an option string containing every `autoLod*` key at its default. A MEL parse error
prints here rather than in a user's session.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add the Auto LOD frame to the P3D export options

Collapsed by default and off by default: a user who never opens the option box
must get exactly the export they got before."
```

---

### Task 5: Auto LOD at export

**Files:**
- Modify: `scripts/a3ob/mayabridge/translator.py`
- Create: `tests/mayapy/export_auto_lod.py`

**Interfaces:**
- Consumes: `generate_auto_lods` (Task 1 location), `undo_suspended` (Task 2),
  the option keys (Task 4).
- Produces: `_auto_lod_settings(options)` mapping the option string onto the dict shape
  `a3ob.mayabridge.autolod.helpers.settings.DEFAULT_SETTINGS` documents.

- [ ] **Step 1: Write the failing test**

```python
"""Auto LOD at export generates, writes, and leaves the scene as it was (mayapy).

The scene must be identical afterwards: same transforms, same names, same set
membership. That assertion is the whole point — "transient" is a promise about the
scene, not about the file.

Run:  mayapy.exe tests/mayapy/export_auto_lod.py
"""

import os
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds



def scene_fingerprint():
    transforms = sorted(cmds.ls(type="transform", long=True) or [])
    sets_ = sorted((s, tuple(sorted(cmds.sets(s, query=True) or [])))
                   for s in cmds.ls(type="objectSet") or [])
    return transforms, sets_


def build():
    cmds.file(new=True, force=True)
    transform = cmds.polySphere(name="garment", r=1, sx=12, sy=12, ch=False)[0]
    cmds.select(transform, replace=True)
    return transform


def export(path, options):
    cmds.file(path, force=True, options=options, type="Arma P3D",
              preserveReferences=False, exportSelected=True)


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    build()
    before = scene_fingerprint()

    path = os.path.join(tempfile.mkdtemp(), "auto.p3d")
    export(path, "autoLod=1;autoLodResolution=1;autoLodGeometry=0;selectedOnly=1")

    _harness.check(os.path.isfile(path), "export wrote no file")
    # Read it the way this suite already does — see tests/mayapy/export_uses_live_mesh.py.
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    with BinaryReader(str(path)) as reader:
        mlod = MLOD.read(reader)
    _harness.check(len(mlod.lods) > 1,
                   "expected a generated LOD stack, got %d LOD(s)" % len(mlod.lods))

    after = scene_fingerprint()
    _harness.check(after[0] == before[0],
                   "generation must leave no transform behind:\n  before=%r\n  after=%r"
                   % (before[0], after[0]))
    _harness.check(after[1] == before[1],
                   "generation must leave set membership untouched")
    print("OK - %d LODs written, scene unchanged" % len(mlod.lods))


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_auto_lod.py`
Expected: FAIL — `expected a generated LOD stack, got 1 LOD(s)`

If it fails earlier on the `cmds.file(... type="Arma P3D" ...)` call, read
`tests/mayapy/export_selection_scope.py` for how this suite drives an export and match it.

- [ ] **Step 3: Implement**

In `translator.py`:

```python
_AUTO_LOD_MENU_KEYS = {
    "autoLodOutput": "output",
    "autoLodReduction": "reduction",
    "autoLodFirst": "first_lod",
    "autoLodGeometryType": "geometry_type",
}
_AUTO_LOD_BOOL_KEYS = {
    "autoLodResolution": ("resolution", True),
    "autoLodGeometry": ("geometry", True),
    "autoLodMemory": ("memory", False),
    "autoLodFire": ("fire_geometry", False),
    "autoLodView": ("view_geometry", False),
}


def _auto_lod_settings(options):
    """Map the option string onto the dict autolod.helpers.settings documents."""
    settings = {}
    for key, name in _AUTO_LOD_MENU_KEYS.items():
        if key in options:
            settings[name] = options[key]
    for key, (name, fallback) in _AUTO_LOD_BOOL_KEYS.items():
        settings[name] = option_enabled(options, key, fallback)
    try:
        settings["fire_quality"] = int(options.get("autoLodFireQuality", 2))
    except (TypeError, ValueError):
        settings["fire_quality"] = 2
    return settings
```

and in `do_write`, wrapping the export:

```python
    if not option_enabled(options, "autoLod", False):
        return MayaMeshExport().export_mlod(expanded_full_name, export_options)

    # Generated LODs are transient: they exist only long enough to be written. Undo is
    # suspended across the whole span so a Ctrl+Z after the export cannot resurrect nodes
    # that were deliberately removed, and cleanup runs in `finally` so a cancel or an
    # exception leaves the scene exactly as the user left it.
    from a3ob.mayabridge.autolod import generate_auto_lods
    from a3ob.mayabridge.undoctl import undo_suspended

    generated = []
    with undo_suspended():
        try:
            generated = generate_auto_lods(_auto_lod_settings(options)) or []
            if not generated:
                om.MGlobal.displayError(
                    "a3ob export: Auto LOD generated nothing — select exactly one source "
                    "mesh. No file was written.")
                return False
            om.MGlobal.setActiveSelectionList(_selection_of(generated),
                                              om.MGlobal.kReplaceList)
            return MayaMeshExport().export_mlod(expanded_full_name, export_options)
        finally:
            for node in generated:
                if cmds.objExists(node):
                    cmds.delete(node)
```

`_selection_of(names)` builds an `MSelectionList` from the generated node names — the
generated LODs, not the original selection, are what must be exported when
`selected_only` is set. Write it as a small helper in the same file.

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_auto_lod.py`
Expected: `OK - N LODs written, scene unchanged`

- [ ] **Step 5: Verify the default path did not move**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify`
Expected: PASS, `5e66ed46ac09f396`/6145116 and `0ba984eb4fdb5d5e`/60229.

**This is the assertion that matters.** `autoLod` defaults to `0`, so the golden fixtures
take the untouched branch. If the bytes moved, the new branch is running when it should not.

- [ ] **Step 6: Verify a cancel leaves nothing behind**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_cancel_leaves_no_debris.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: generate Auto LODs at export, transiently

Generated LODs live only long enough to be written: undo is suspended across
the span so Ctrl+Z cannot resurrect them, and cleanup runs in finally so a
cancel or an exception leaves the scene exactly as it was. The test asserts the
scene fingerprint — transforms and set membership — is identical afterwards,
because 'transient' is a promise about the scene, not the file.

Off by default; the byte gate confirms a default export is unchanged."
```

---

### Task 6: Optional texture import

**Files:**
- Modify: `scripts/a3ob/mayabridge/translator.py` (`do_read`)
- Modify: `scripts/mayaObjectBuilderP3DOptions.mel` (`Import: Data` frame)
- Create: `tests/mayapy/import_textures_optional.py`

- [ ] **Step 1: Write the failing test**

```python
"""Texture import is opt-out (run with mayapy).

Decoding .paa and wiring file nodes is the slow part of an import. It stays ON by
default — existing behaviour — but a user who does not want it must be able to say so.

Run:  mayapy.exe tests/mayapy/import_textures_optional.py
"""

import os
import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds

FIXTURE = os.path.join(_harness.REPO, "Arma3ObjectBuilder-master", "tests", "inputs",
                       "p3d", "sample_1_character.p3d")


def import_with(options):
    cmds.file(new=True, force=True)
    cmds.file(FIXTURE, i=True, type="Arma P3D", ignoreVersion=True,
              mergeNamespacesOnClash=False, options=options)
    cmds.refresh()


def main():
    if not os.path.isfile(FIXTURE):
        print("SKIP - fixture absent (clone Arma3ObjectBuilder-master): %s" % FIXTURE)
        sys.exit(0)
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))

    import a3ob.mayabridge.paatex as paatex
    calls = []
    original = paatex.assign_pending_textures
    paatex.assign_pending_textures = lambda *a, **k: calls.append(1)
    try:
        import_with("importTextures=0")
        cmds.evalDeferred(lambda: None, lowestPriority=True)
        _harness.check(not calls,
                       "importTextures=0 must not schedule texture assignment, got %r"
                       % (calls,))

        import_with("importTextures=1")
        cmds.evalDeferred(lambda: None, lowestPriority=True)
        _harness.check(calls,
                       "importTextures=1 must schedule texture assignment")
    finally:
        paatex.assign_pending_textures = original
    print("OK - texture assignment follows importTextures")


main()
```

**If patching `paatex.assign_pending_textures` does not intercept the call**, it is because
`do_read` schedules it by string through `cmds.evalDeferred`, which re-imports the module in
a fresh namespace. In that case assert on the observable outcome instead — count `file`
nodes after the deferred queue drains — and say in your report that you changed approach and
why. Do not report a green from a patch that never fired.

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/import_textures_optional.py`
Expected: FAIL on the first check — the option is not read yet, so textures are always
scheduled.

- [ ] **Step 3: Gate the deferred call**

In `translator.do_read`, the block that schedules texture assignment becomes conditional on
`option_enabled(options, "importTextures", True)`. Default `True` — existing scenes and
habits are unaffected.

- [ ] **Step 4: Add the checkbox**

In the `Import: Data` frame of `mayaObjectBuilderP3DOptions.mel`, add
`checkBox -label "Import Textures (.paa decode)" mayaObjectBuilderImportTextures;` and wire
it in `SetOptions` / `GetOptions` with default `"1"`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/import_textures_optional.py`
Expected: `OK - texture assignment follows importTextures`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: make .paa texture import optional

On by default, so nothing changes for anyone who does not go looking."
```

---

### Task 7: A third severity

**Files:**
- Modify: `scripts/a3ob/mayabridge/commands/validate.py`
- Modify: `tests/mayapy/validate_lost_rig.py` (the posed-rig and empty-set rows move tier)
- Create: `tests/mayapy/validate_severities.py`

**Interfaces:**
- Produces: `_IssueLog.damage(node, message)`, `.damages` count, and rows of the form
  `"damage|node|message"`. Task 8 consumes them.

- [ ] **Step 1: Write the failing test**

```python
"""Issues that silently change the exported file get their own severity (mayapy).

On a measured scene a3obValidate reported 0 errors and 21 warnings — so "errors block
the export" would never once have fired, while two camo selections silently did not
reach the P3D. A two-level scheme cannot express "this file will be written, and it
will quietly not be what you think it is".

Run:  mayapy.exe tests/mayapy/validate_severities.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_posed_rig():
    cmds.file(new=True, force=True)
    transform = cmds.polyCylinder(name="garment", r=1, h=4, sx=8, sy=4, ch=False)[0]
    for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                       ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=name, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)
    cmds.setAttr(tip + ".rotateX", 35)   # pose it: export would bake this in
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    build_posed_rig()

    rows = cmds.a3obValidate() or []
    posed = [r for r in rows if "pose" in r.lower()]
    _harness.check(posed, "a posed rig must be reported at all, got %r" % (rows,))
    _harness.check(posed[0].startswith("damage|"),
                   "a posed rig silently bakes the pose into the export — that is damage, "
                   "not a warning: %r" % (posed[0],))

    # An empty Object Builder set: its selection simply will not reach the P3D.
    empty = cmds.sets(name="a3ob_SEL_gone", empty=True)
    cmds.addAttr(empty, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(empty + ".a3obSelectionName", "camo_gone", type="string")
    rows = cmds.a3obValidate() or []
    lost = [r for r in rows if "no live members" in r]
    _harness.check(lost, "an empty selection set must be reported, got %r" % (rows,))
    _harness.check(lost[0].startswith("damage|"),
                   "a selection that will not reach the file is damage: %r" % (lost[0],))
    print("OK - posed rig and empty selection both reported as damage")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_severities.py`
Expected: FAIL — `that is damage, not a warning: 'warning|...'`

- [ ] **Step 3: Add the tier**

In `_IssueLog`, beside `warn` and `error`:

```python
    def damage(self, node, message):
        """The file will be written, and will quietly differ from what the scene shows.

        Distinct from a warning because export ASKS before proceeding on one of these, and
        distinct from an error because the file is not malformed — it is just not what the
        user thinks they exported."""
        self._record("damage", node, message)
        om.MGlobal.displayWarning("a3obValidate: %s%s" % (message, (" on " + node) if node else ""))

    @property
    def damages(self):
        return sum(1 for severity, _, _ in self.items if severity == "damage")
```

Then move exactly two call sites from `log.warn` to `log.damage`: the posed-rig report and
the "Object Builder set has no live members and will be ignored" report. **Move no others** —
`duplicate LOD resolution signature` and the skin-outlier report change nothing about the
file and stay warnings.

- [ ] **Step 4: Teach the panel the new severity**

`scripts/a3ob/ui/panels/validation.py`'s `_populate_validation` splits on `"|"` and treats
anything not `"error"` as a warning, so `damage` rows will already display — but with the
warning icon and counted as warnings. Give `damage` its own icon and its own count in the
summary line. Read the existing `errors`/`warnings` counters and follow their shape.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_severities.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_lost_rig.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
python tests/run_all.py
```
Expected: pass, 41/41 plus the new file. `validate_lost_rig.py` may need its assertions
updated if any row it checks moved tier — update them to the tier the row now carries, and
say which in your report.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add a damage severity between warning and error

On the measured scene validation reported 0 errors and 21 warnings, so
'errors block the export' would never have fired while two camo selections
silently failed to reach the file. Damage is for exactly that: the file gets
written and quietly is not what the scene shows."
```

---

### Task 8: Export always validates, and can refuse

**Files:**
- Modify: `scripts/a3ob/mayabridge/translator.py`
- Modify: `scripts/mayaObjectBuilderP3DOptions.mel` — remove the three gating checkboxes
- Create: `tests/mayapy/export_blocks_on_error.py`

**Interfaces:**
- Consumes: `_IssueLog` rows including `damage` (Task 7).
- Produces: `do_write` returning `False` without writing when validation refuses.

- [ ] **Step 1: Write the failing test**

```python
"""Export validates every time, and refuses to write a malformed file (mayapy).

Validation used to be gated on three checkboxes that all defaulted to off, and the
result was discarded even when they were on — so nothing could ever stop a bad file
being written.

Run:  mayapy.exe tests/mayapy/export_blocks_on_error.py
"""

import os
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_lod_with_bad_mass():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="crate", ch=False)[0]
    for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                       ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=name, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obLodType", 6)      # Geometry LOD
    cmds.addAttr(transform, longName="a3obMassValues", dataType="string")
    cmds.setAttr(transform + ".a3obMassValues", "-5.0", type="string")  # negative: an error
    cmds.select(transform, replace=True)
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    build_lod_with_bad_mass()

    rows = cmds.a3obValidate() or []
    _harness.check(any(r.startswith("error|") for r in rows),
                   "fixture must produce a real error or this test proves nothing: %r" % (rows,))

    path = os.path.join(tempfile.mkdtemp(), "blocked.p3d")
    cmds.file(path, force=True, options="selectedOnly=1", type="Arma P3D",
              preserveReferences=False, exportSelected=True)
    _harness.check(not os.path.isfile(path),
                   "an export with a validation error must write no file")
    print("OK - export refused to write a file with a validation error")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_blocks_on_error.py`
Expected: FAIL — `an export with a validation error must write no file`

If it fails on the first check instead, the fixture does not actually produce an error —
read `validate.py`'s error call sites and build a fixture that hits one. A test that cannot
fail proves nothing.

- [ ] **Step 3: Implement**

In `do_write`, replace the gated block. Read the result instead of discarding it:

The current code calls `om.MGlobal.executeCommand(command)`, which does not hand back the
command's string array. Call the command through `maya.cmds` instead so the rows are
available. Note that under `mayapy` an `MPxCommand` result comes back as a list where
interactive Maya may give a scalar — handle both.

```python
    issues = cmds.a3obValidate(selectionOnly=export_options.selected_only) or []
    errors = [row for row in issues if row.startswith("error|")]
    damages = [row for row in issues if row.startswith("damage|")]

    if errors:
        om.MGlobal.displayError(
            "a3ob export: %d validation error(s); no file written. First: %s"
            % (len(errors), errors[0].split("|", 2)[-1]))
        return False

    if damages and not _confirm_damage(damages):
        om.MGlobal.displayWarning("a3ob export: cancelled; no file written.")
        return False
```

and:

```python
def _confirm_damage(damages):
    """Ask before writing a file that will quietly differ from the scene.

    Batch mode cannot show a dialog and nobody is there to answer one, so a scripted
    export reports and proceeds rather than hanging forever on a prompt."""
    if cmds.about(batch=True):
        for row in damages:
            om.MGlobal.displayWarning("a3ob export: %s" % row.split("|", 2)[-1])
        return True
    listing = "\n".join("  - " + row.split("|", 2)[-1] for row in damages[:10])
    if len(damages) > 10:
        listing += "\n  ... and %d more" % (len(damages) - 10)
    answer = cmds.confirmDialog(
        title="Export anyway?",
        message="This export will be written, but will differ from your scene:\n\n%s"
                % listing,
        button=["Export anyway", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Export anyway"
```

- [ ] **Step 4: Remove the dead gating options**

Delete `validateMeshes`, `exportValidateMeshes` and `validateLods` from
`mayaObjectBuilderP3DOptions.mel` — the controls, the `SetOptions` branches and the
`GetOptions` lines. **These three only.** The other unwired keys stay: they are stubs for
planned features, per `docs/specs/2026-07-20-ui-simplification-design.md`.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_blocks_on_error.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_selection_scope.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
python tests/run_all.py
```

`golden.py verify` is the one to watch: the fixtures must still validate cleanly enough to
export. **If the gate now fails because a fixture produces an error, do not weaken the
check** — report it. It would mean a fixture the byte contract depends on is invalid, which
is worth knowing.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: validate on every export, and refuse to write a bad file

Validation was gated on three checkboxes that all defaulted to off, and the
result was thrown away even when they were on — nothing could ever stop a bad
file being written. Errors now block; damage asks; batch mode reports and
proceeds, because a scripted export must not hang on a dialog nobody can
answer."
```

---

### Task 9: Hoist the scene-global checks

**Files:**
- Modify: `scripts/a3ob/mayabridge/commands/validate.py`
- Create: `tests/mayapy/validate_reports_once.py`

- [ ] **Step 1: Write the failing test**

```python
"""A scene-global issue is reported once, not once per LOD (mayapy).

_validate_object_sets runs per mesh and walks EVERY set in the scene, so an empty set
was reported once per LOD — 21 rows on a six-LOD scene where a handful of problems
existed. Every set was also inspected once per LOD: 245 inspections where 35 would do.

Run:  mayapy.exe tests/mayapy/validate_reports_once.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_lods(count):
    cmds.file(new=True, force=True)
    for index in range(count):
        transform = cmds.polyCube(name="lod%d" % index, ch=False)[0]
        for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                           ("a3obResolution", "long")):
            cmds.addAttr(transform, longName=name, attributeType=kind)
        cmds.setAttr(transform + ".a3obIsLOD", True)
        cmds.setAttr(transform + ".a3obResolution", index + 1)
    empty = cmds.sets(name="a3ob_SEL_gone", empty=True)
    cmds.addAttr(empty, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(empty + ".a3obSelectionName", "camo_gone", type="string")


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))

    build_lods(6)
    rows = [r for r in (cmds.a3obValidate() or []) if "no live members" in r]
    _harness.check(len(rows) == 1,
                   "one empty set in a 6-LOD scene must be reported ONCE, got %d: %r"
                   % (len(rows), rows))

    # And the count must not scale with LOD count.
    build_lods(2)
    rows_small = [r for r in (cmds.a3obValidate() or []) if "no live members" in r]
    _harness.check(len(rows_small) == 1,
                   "still once with 2 LODs, got %d" % len(rows_small))
    print("OK - scene-global issues reported once regardless of LOD count")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_reports_once.py`
Expected: FAIL — `must be reported ONCE, got 6`

- [ ] **Step 3: Split the per-mesh pass**

`_validate_object_sets(self, mesh, lod_name, proxy_placeholders, log)` currently mixes two
kinds of check while iterating every set in the scene:

- **scene-global:** `metadata_set_has_live_members` → "has no live members and will be
  ignored". Depends on nothing about `mesh`.
- **per-mesh:** everything under `set_contains_mesh(set_obj, mesh)` — duplicate selection
  names, proxy selection validity, flag component type, flag value.

Extract the global half into a method called ONCE from `doIt`, after the LOD loop. Leave the
per-mesh half where it is. Do not deduplicate the output as a workaround — that would hide
the repeated scan while keeping its cost.

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_reports_once.py`
Expected: `OK - scene-global issues reported once regardless of LOD count`

- [ ] **Step 5: Confirm nothing else moved**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_severities.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_lost_rig.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
python tests/run_all.py
```
Expected: pass. Per-mesh checks must still fire per mesh — a proxy problem on one LOD and
not another must still be reported for the right one.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "fix: report scene-global validation issues once

_validate_object_sets ran per mesh and walked every set in the scene, so an
empty set was reported once per LOD and every set was inspected once per LOD —
245 inspections where 35 would do on the measured scene. Hoisted rather than
deduplicated: deduplicating would have hidden the symptom and kept the cost."
```

---

### Task 10: Remove Auto LOD from the dock, and gates

**Files:**
- Modify: `scripts/a3ob/ui/dock.py` — drop the `"Auto LOD"` panel entry and the Quick
  Actions button
- Modify: `scripts/a3ob/ui/panels/lod.py` — remove `_build_auto_lod_section` and
  `auto_lod_settings`
- Modify: `scripts/a3ob/ui/actions/lod.py` — remove `generate_auto_lods_from_ui`
- Modify: `scripts/a3ob/ui/entry.py` if it re-exports either

- [ ] **Step 1: Check what still calls them**

```bash
grep -rn "generate_auto_lods_from_ui\|auto_lod_settings\|_build_auto_lod_section" \
  scripts/ tests/ plug-ins/ --include=*.py
```
Handle every hit. `scripts/objectBuilderAutoLOD.py` is an external facade — read it before
touching it; if it exposes the generator itself rather than the UI wrapper, it stays.

- [ ] **Step 2: Remove them**

Delete the `("Auto LOD", self._build_auto_lod_section(), True, None)` entry from `dock.py`'s
`panels` list, the `"Auto LOD"` entry from `_build_quick_actions`, and the two methods from
`panels/lod.py`, plus `generate_auto_lods_from_ui` from `actions/lod.py` and its `__all__`
entry.

- [ ] **Step 3: Verify the dock still builds**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
```
Expected: pass.

- [ ] **Step 4: Full suite**

Run: `python tests/run_all.py`
Expected: zero failures.

- [ ] **Step 5: Byte gate**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify`
Expected: PASS, `5e66ed46ac09f396`/6145116 and `0ba984eb4fdb5d5e`/60229. **Never `capture`.**

- [ ] **Step 6: Line endings**

```bash
git diff --shortstat main..HEAD
git diff --shortstat --ignore-cr-at-eol main..HEAD
```
Expected: the two agree.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: remove the Auto LOD panel from the dock

Generation happens at export now. Phase 2 complete."
```

---

## Self-review notes

**Spec coverage.** Auto LOD option box (Task 4), Auto LOD at export with transient cleanup
and undo suspension (Task 5), the non-consuming refactor it depends on (Task 3), the undo
helper relocation the spec names (Task 2), `importTextures` (Task 6), three severities
(Task 7), validation always on with errors blocking and damage asking (Task 8), the
scene-global hoist (Task 9), the dock removal (Task 10).

**Task 1 is not in either spec.** It is a structural precondition discovered while writing
this plan: `autolod` lived under `a3ob/ui/`, and `mayabridge` must not import from there.
The package was already self-contained, so it is a relocation.

**Deliberately deferred to Phase 3.** The specs' split Export button, the
`defaultFileExportActiveType` optionVar fix, and the Quick Actions removal all belong to the
presentation spec, not here — Task 10 removes only the Auto LOD panel.

**Not covered, and not an oversight.** The specs also describe Export Selection as Auto
LOD's coherent pairing. Nothing here forces it: both access modes work, and the choice is a
UI affordance that Phase 5 delivers.
