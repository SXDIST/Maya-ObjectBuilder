# Weights as Mesh Data — Implementation Plan

> **EXECUTED — this plan is spent.** The unticked checkboxes below are a bookkeeping artifact,
> not remaining work: the feature shipped and is covered by
> `tests/mayapy/{weight_sync,weights_restore,weights_survive_skeleton}.py`. Kept for the
> reasoning behind the design. Do not re-execute it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Maya mesh the source of truth for DayZ skin weights, so neither the skeleton nor the reference body has to be present in the scene for the plugin to work correctly.

**Architecture:** `.p3d` stores weights as named vertex selections and knows nothing about skeletons. Today the truth lives in the `skinCluster`, which Maya deletes together with the joints. These tasks move the truth onto the mesh (`a3obBakedWeights`), keep the `skinCluster` as an editing tool that always wins while it exists, and let the reference body be loaded from file on demand.

**Tech Stack:** Maya 2027, Python 3, `maya.api.OpenMaya` (API 2.0), `maya.cmds`. Pure-Python format code in `scripts/a3ob/formats/`. Tests: `tests/python/*.py` (plain interpreter) and `tests/mayapy/*.py` (mayapy).

**Source spec:** `docs/specs/2026-07-19-weights-as-mesh-data-design.md`

## Global Constraints

- Full validation after every task: `tests/python` → `py_compile` → `tests/mayapy`. Run the WHOLE suite, not just the new test — the `MComputation` breakage surfaced in an unrelated workflow test.
- Export output must stay **byte-identical** unless a task explicitly changes it. Compare against a baseline captured before the change.
- DayZ weight rules: at most 4 influences per vertex, normalized, nothing in `(0, 1/254]`.
- The live `skinCluster` always takes precedence over stored weights. Stored weights must never override a rig that is still present.
- Export must not silently change the user's scene. Any write during export is a deliberate, documented decision.
- Commands that mutate the scene follow the existing undo rules in `commands/helpers/base.py`: `_UndoableBase` routes everything through its `MDagModifier`, or the command stays non-undoable and wraps its body in `undo_chunk()`. Never mix.
- Work on branch `skinning-and-native-cleanup` (or a branch from it). Do not commit to `main`.

**Scope note:** This plan covers stages 1–3 of the spec. Stages 4 (UI revision) and 5 (remaining C++-port habits) depend on what 1–3 leave behind and get their own plan once these land.

---

### Task 1: Keep stored weights fresh automatically

Today `a3obBakeSkin` must be remembered before deleting a rig. Sync on scene save instead, so the stored copy is current without the user thinking about it.

Scene save is the sync point rather than export: export writing to the scene would make a read-only-looking operation mutate the user's data, and Maya already expects a save to touch the file.

**Files:**
- Create: `scripts/a3ob/mayabridge/weightsync.py`
- Modify: `plug-ins/MayaObjectBuilder.py` (register/deregister the callback)
- Test: `tests/mayapy/weight_sync.py`

**Interfaces:**
- Consumes: `skinweights.bake_string(names, weights, influence_count)`, `commands.skin.read_skin(mesh_path)`, `attributes.set_string`, `A.BAKED_WEIGHTS`.
- Produces: `weightsync.sync_all_lods() -> int` (LODs updated), `weightsync.install() -> None`, `weightsync.uninstall() -> None`.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/weight_sync.py`:

```python
"""Stored weights are refreshed on scene save (run with mayapy).

a3obBakeSkin exists, but it has to be remembered before deleting a rig. Saving the
scene refreshes the stored copy automatically, so the weights on disk are always
current and deleting a skeleton stops being an event.

Run:  mayapy.exe tests/mayapy/weight_sync.py
"""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build():
    cmds.file(new=True, force=True)
    transform = cmds.polyCylinder(name="synced", r=1, h=4, sx=8, sy=4, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)
    return transform


def main():
    cmds.loadPlugin(os.path.join(_REPO, "plug-ins", "MayaObjectBuilder.py"))
    from a3ob.mayabridge import weightsync

    transform = build()
    check(not cmds.attributeQuery("a3obBakedWeights", node=transform, exists=True),
          "nothing should be stored before the first sync")

    updated = weightsync.sync_all_lods()
    check(updated == 1, "expected 1 LOD synced, got %r" % (updated,))
    stored = cmds.getAttr(transform + ".a3obBakedWeights")
    check("Pelvis" in stored and "Spine" in stored,
          "both bones must be stored, got %r" % (stored[:80],))

    # Editing weights and syncing again must refresh, not append.
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    skin = cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")[0]
    cmds.skinPercent(skin, "%s.vtx[0]" % shape, transformValue=[("Pelvis", 1.0), ("Spine", 0.0)])
    weightsync.sync_all_lods()
    refreshed = cmds.getAttr(transform + ".a3obBakedWeights")
    check(refreshed != stored, "a weight edit must change the stored copy")
    check(refreshed.count("Pelvis:") == 1, "syncing must replace, not append")

    # Saving the scene must sync without an explicit call.
    weightsync.install()
    try:
        cmds.skinPercent(skin, "%s.vtx[1]" % shape, transformValue=[("Pelvis", 1.0), ("Spine", 0.0)])
        before_save = cmds.getAttr(transform + ".a3obBakedWeights")
        scene = os.path.join(tempfile.mkdtemp(prefix="sync-"), "scene.ma")
        cmds.file(rename=scene)
        cmds.file(save=True, type="mayaAscii", force=True)
        after_save = cmds.getAttr(transform + ".a3obBakedWeights")
        check(after_save != before_save, "saving the scene must refresh the stored weights")
    finally:
        weightsync.uninstall()

    # And uninstall must remove the callback.
    cmds.skinPercent(skin, "%s.vtx[2]" % shape, transformValue=[("Pelvis", 1.0), ("Spine", 0.0)])
    frozen = cmds.getAttr(transform + ".a3obBakedWeights")
    cmds.file(save=True, type="mayaAscii", force=True)
    check(cmds.getAttr(transform + ".a3obBakedWeights") == frozen,
          "no callback may survive uninstall()")

    print("OK weights sync on save and the callback is removable")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL weight_sync: %s" % error, file=sys.stderr)
        raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weight_sync.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'a3ob.mayabridge.weightsync'`

- [ ] **Step 3: Write the module**

Create `scripts/a3ob/mayabridge/weightsync.py`:

```python
"""Keep the stored copy of skin weights current.

Weights live in the skinCluster, which Maya deletes together with the joints — so a
stored copy is what lets a model survive losing its rig. Baking by hand means
remembering to do it; syncing on scene save means the stored copy is simply always
current.

Scene save is the sync point on purpose. Doing it during export would make an
operation that looks read-only mutate the user's scene, while a save is already
expected to write.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge import skinweights as sw
from a3ob.mayabridge.attributes import A

_callback_ids = []


def sync_all_lods():
    """Refresh a3obBakedWeights on every LOD that still has a live skinCluster.

    Returns how many LODs were updated. LODs without a skinCluster are left alone:
    their stored weights are the only copy left and must not be cleared."""
    from a3ob.mayabridge.commands.skin import read_skin

    updated = 0
    for lod in cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []:
        shapes = cmds.listRelatives(lod, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []
        if not shapes:
            continue
        selection = om.MSelectionList()
        selection.add(shapes[0])
        mesh_path = selection.getDagPath(0)
        skin = read_skin(mesh_path)
        if skin is None:
            continue
        skin_fn, weights, influence_count, _neighbours = skin
        names = [p.partialPathName().split("|")[-1].split(":")[-1]
                 for p in skin_fn.influenceObjects()]
        text = sw.bake_string(names, weights, influence_count)
        if not text:
            continue
        node = om.MSelectionList()
        node.add(lod)
        attr.set_string(node.getDependNode(0), A.BAKED_WEIGHTS, text)
        updated += 1
    return updated


def _on_before_save(*_args):
    try:
        sync_all_lods()
    except Exception:  # noqa: BLE001 - a sync failure must never block saving the scene
        pass


def install():
    """Sync before every scene save. Idempotent."""
    if _callback_ids:
        return
    _callback_ids.append(
        om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeSave, _on_before_save))


def uninstall():
    """Remove the callback. MUST run on plugin unload — a surviving callback fires
    into freed Python objects and takes Maya down."""
    while _callback_ids:
        try:
            om.MMessage.removeCallback(_callback_ids.pop())
        except Exception:  # noqa: BLE001 - already gone, or Maya is tearing down
            pass


__all__ = ["sync_all_lods", "install", "uninstall"]
```

- [ ] **Step 4: Register the callback with the plugin**

In `plug-ins/MayaObjectBuilder.py`, inside `initializePlugin`, after `_load_translator_plugin()`:

```python
    from a3ob.mayabridge import weightsync   # noqa: E402
    weightsync.install()
```

And inside `uninitializePlugin`, before the command deregistration loop:

```python
    try:
        from a3ob.mayabridge import weightsync
        weightsync.uninstall()
    except Exception as error:  # noqa: BLE001
        om.MGlobal.displayWarning("weightsync uninstall: %s" % error)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weight_sync.py`
Expected: `OK weights sync on save and the callback is removable`

- [ ] **Step 6: Verify export is unchanged**

Export the character fixture before and after this task and compare bytes. Reuse the bench script pattern:

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py`
Expected: 14 `OK` lines, no `FAIL`

- [ ] **Step 7: Run the full suite**

```bash
python tests/python/test_skinweights.py && python tests/python/test_p3d_roundtrip.py && python tests/python/test_model_cfg.py
python -m py_compile $(find scripts plug-ins tests -name '*.py')
for t in weight_sync weights_survive_skeleton skin_transfer scene_watch command_undo command_correctness export_uses_live_mesh dock_refresh_cost skin_weights_workflow p3d_workflow model_cfg_workflow; do
  "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/$t.py 2>&1 | grep -aE "^OK|^FAIL"
done
```

Expected: every line starts with `OK`, none with `FAIL`.

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/mayabridge/weightsync.py plug-ins/MayaObjectBuilder.py tests/mayapy/weight_sync.py
git commit -m "feat: refresh stored skin weights on scene save

Baking weights by hand means remembering to do it before deleting a rig. Syncing
on kBeforeSave keeps the stored copy current without the user thinking about it,
so losing a skeleton stops being an event.

Scene save is the sync point rather than export: export writing to the scene
would make a read-only-looking operation mutate the user's data.

LODs without a skinCluster are skipped — their stored weights are the only copy
left and must not be cleared."
```

---

### Task 2: Load the reference body from file when the scene has none

`a3obTransferSkin` currently requires the body to be in the scene. The reference is already saved as a `.ma`; load it on demand and remove it again.

**Files:**
- Modify: `scripts/a3ob/mayabridge/skintransfer.py` (add `borrowed_reference`)
- Modify: `scripts/a3ob/mayabridge/commands/skin.py` (`TransferSkinCommand.doIt`)
- Test: `tests/mayapy/skin_transfer.py` (add a case)

**Interfaces:**
- Consumes: `references.add_reference(kind)`, `references.reference_path(kind)`, `skintransfer.find_reference(targets, explicit)`.
- Produces: `skintransfer.borrowed_reference(targets, explicit="", kind="male_body")` — a context manager yielding an `MDagPath` to the reference mesh, deleting anything it imported on exit.

- [ ] **Step 1: Write the failing test**

Append to `tests/mayapy/skin_transfer.py`, and call it from `main()` before the final `print`:

```python
def test_reference_borrowed_from_file():
    """The body need not be in the scene: the saved reference is loaded, used, removed."""
    import maya.api.OpenMaya as om
    from a3ob.mayabridge import references, skintransfer

    body, body_skin, garment = build_scene()

    # Save the body as the reference asset, then remove it from the scene entirely.
    cmds.select(body, replace=True)
    references.save_reference("male_body")
    cmds.delete(body)
    check(not cmds.objExists(body), "the body must be gone from the scene")

    before = set(cmds.ls(assemblies=True) or [])
    cmds.select(garment, replace=True)
    targets = skintransfer.selected_mesh_shapes()
    with skintransfer.borrowed_reference(targets) as reference:
        check(reference is not None, "a reference must be produced from the saved file")
        count, _rigid = skintransfer.transfer_to_target(targets[0], reference)
        check(count > 0, "transfer must run against the borrowed reference")

    after = set(cmds.ls(assemblies=True) or [])
    check(after == before, "the borrowed reference must be removed again, left %r"
          % (after - before,))

    skin = skintransfer.skin_cluster_of(targets[0])
    check(skin, "the garment must still carry the transferred skinCluster")
    print("OK reference borrowed from file and cleaned up")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_transfer.py`
Expected: FAIL with `AttributeError: module 'a3ob.mayabridge.skintransfer' has no attribute 'borrowed_reference'`

- [ ] **Step 3: Implement the context manager**

Add to `scripts/a3ob/mayabridge/skintransfer.py`:

```python
import contextlib


@contextlib.contextmanager
def borrowed_reference(targets, explicit="", kind="male_body"):
    """Yield a reference mesh, importing the saved asset if the scene has none.

    Anything imported here is deleted on exit, so the body stops being something the
    user has to keep in the scene. A reference already present is used as-is and
    never touched."""
    from a3ob.mayabridge import references

    try:
        yield find_reference(targets, explicit)
        return
    except ValueError:
        pass  # nothing suitable in the scene — fall through and borrow one

    if not references.reference_path(kind):
        raise ValueError(
            "no skinned reference in the scene and no %s reference saved — add the body, or "
            "save one with a3obReference" % references.KINDS[kind][1])

    imported = references.add_reference(kind)
    try:
        yield find_reference(targets, explicit)
    finally:
        existing = [node for node in imported if cmds.objExists(node)]
        if existing:
            cmds.delete(existing)
```

Export it by adding `"borrowed_reference",` to `__all__`.

- [ ] **Step 4: Use it in the command**

In `scripts/a3ob/mayabridge/commands/skin.py`, replace the `find_reference` block in `TransferSkinCommand.doIt` (the `try:` that produces `reference` and returns on `ValueError`) and the transfer loop with:

```python
        done = 0
        try:
            with skintransfer.borrowed_reference(targets, explicit) as reference:
                reference_key = reference.fullPathName()
                # One Ctrl+Z must undo the whole transfer, not each internal cmds call.
                with undo_chunk():
                    for target in targets:
                        if target.fullPathName() == reference_key:
                            continue  # never rewrite the reference body itself
                        try:
                            count, rigid = skintransfer.transfer_to_target(
                                target, reference, distance)
                        except ValueError as error:
                            om.MGlobal.displayError("a3obTransferSkin: %s" % error)
                            continue
                        done += 1
                        om.MGlobal.displayInfo(
                            "a3obTransferSkin: %s <- %s (%d verts, %d rigid shell(s))"
                            % (target.partialPathName(), reference.partialPathName(),
                               count, rigid))
        except ValueError as error:
            om.MGlobal.displayError("a3obTransferSkin: %s" % error)
            self.setResult(0)
            return
```

- [ ] **Step 5: Run test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_transfer.py`
Expected: both `OK skin transfer: ...` and `OK reference borrowed from file and cleaned up`

- [ ] **Step 6: Run the full suite**

Same command block as Task 1 Step 7. Expected: all `OK`.

- [ ] **Step 7: Commit**

```bash
git add scripts/a3ob/mayabridge/skintransfer.py scripts/a3ob/mayabridge/commands/skin.py tests/mayapy/skin_transfer.py
git commit -m "feat: transfer borrows the reference body from file when absent

The body no longer has to be kept in the scene. When nothing suitable is present,
the saved reference asset is imported, used, and deleted again; a reference that
is already there is used as-is and never touched."
```

---

### Task 3: Import stores weights as mesh data

Import currently builds a `skinCluster` only, so a `.p3d` opened without its skeleton loses its weights on the next export. Store them on the LOD as well, always.

**Files:**
- Modify: `scripts/a3ob/mayabridge/import_/convert/mesh.py` (`set_lod_metadata`)
- Test: `tests/mayapy/weights_survive_skeleton.py` (add a case)

**Interfaces:**
- Consumes: `skinweights.bake_string`, `A.BAKED_WEIGHTS`, the LOD's `vertex_map` (Maya index -> P3D source index) already passed to `set_lod_metadata`.
- Produces: nothing new; `a3obBakedWeights` is populated at import time.

- [ ] **Step 1: Write the failing test**

Append to `tests/mayapy/weights_survive_skeleton.py`, and call it from `main()`:

```python
def test_import_stores_weights_on_mesh():
    """A .p3d imported without a skeleton must keep its weights as mesh data."""
    from pathlib import Path
    from a3ob.mayabridge.import_.importer import MayaMeshImport
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD

    fixture = (Path(_REPO) / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d"
               / "sample_1_character.p3d")
    if not fixture.is_file():
        print("SKIP import weight storage: fixture missing")
        return

    with BinaryReader(str(fixture)) as reader:
        mlod = MLOD.read(reader)
    expected = {tagg.name for lod in mlod.lods for tagg in lod.taggs
                if isinstance(tagg.name, str) and not tagg.name.startswith("#")
                and tagg.data is not None and tagg.data.kind == "Selection"}

    cmds.file(new=True, force=True)
    MayaMeshImport().import_mlod(mlod, str(fixture))

    stored_bones = set()
    for lod in cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []:
        if not cmds.attributeQuery("a3obBakedWeights", node=lod, exists=True):
            continue
        text = cmds.getAttr(lod + ".a3obBakedWeights") or ""
        stored_bones.update(name for name, _pairs in
                            __import__("a3ob.mayabridge.skinweights", fromlist=["x"])
                            .parse_bake_string(text))

    check(stored_bones, "import must store weights on the LOD transforms")
    check(stored_bones <= expected,
          "stored bones must all come from the file: %r" % sorted(stored_bones - expected))
    print("OK import stores %d bone selection(s) as mesh data" % len(stored_bones))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_survive_skeleton.py`
Expected: FAIL with `import must store weights on the LOD transforms`

- [ ] **Step 3: Store the weights during import**

In `scripts/a3ob/mayabridge/import_/convert/mesh.py`, inside `set_lod_metadata`, after the existing `attr.set_string(transform, A.PROPERTIES, ...)` line, add:

```python
    # Weight selections are stored on the transform as well as being turned into a
    # skinCluster later. The skinCluster dies with the skeleton; this copy does not, so a
    # .p3d opened without its rig still exports its weights.
    bone_rows = []
    for tagg in lod.taggs:
        if tagg.data is None or tagg.data.kind != "Selection" or tagg.is_proxy():
            continue
        if not isinstance(tagg.name, str) or tagg.name.startswith("#"):
            continue
        pairs = []
        for source_index, weight in tagg.data.vertex_weights:
            mapped = source_index if not vertex_map else None
            if vertex_map:
                for maya_index, mapped_source in enumerate(vertex_map):
                    if mapped_source == source_index:
                        mapped = maya_index
                        break
            if mapped is not None and weight > 0.0:
                pairs.append("%d=%s" % (mapped, repr(float(weight))))
        if pairs:
            bone_rows.append("%s:%s" % (tagg.name, ",".join(pairs)))
    if bone_rows:
        attr.set_string(transform, A.BAKED_WEIGHTS, ";".join(bone_rows))
```

Note: `vertex_map` is the list already passed in (Maya index -> P3D source index). The inner
loop is O(n²) on large LODs; if the full-suite run shows import time regressing past ~1.5 s on
the character fixture, replace it with a reverse dict built once before the loop:

```python
    reverse = {source: maya for maya, source in enumerate(vertex_map or [])}
```

and use `reverse.get(source_index)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_survive_skeleton.py`
Expected: three `OK` lines, including `OK import stores N bone selection(s) as mesh data`

- [ ] **Step 5: Verify export is still byte-identical**

Stored weights must not change what a rigged export writes — the live skinCluster wins.

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py`
Expected: 14 `OK` lines. If the round-trip test fails, the fallback ordering is wrong: check that `_add_skin_weight_taggs` runs before `_add_baked_weight_taggs` in `lodexport.py`.

- [ ] **Step 6: Measure import time**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "
import sys,time; sys.path.insert(0,'scripts')
import maya.standalone as s; s.initialize()
import maya.cmds as cmds
cmds.loadPlugin('plug-ins/MayaObjectBuilder.py')
from a3ob.formats.binary import BinaryReader
from a3ob.formats.p3d import MLOD
from a3ob.mayabridge.import_.importer import MayaMeshImport
f='Arma3ObjectBuilder-master/tests/inputs/p3d/sample_1_character.p3d'
r=BinaryReader(f); m=MLOD.read(r); r.close()
cmds.file(new=True,force=True); MayaMeshImport().import_mlod(m,f)
cmds.file(new=True,force=True)
t=time.perf_counter(); MayaMeshImport().import_mlod(m,f); print('IMPORT %.3fs'%(time.perf_counter()-t))
"
```

Expected: under 1.5 s (baseline was 0.58 s). If slower, apply the reverse-dict variant from Step 3.

- [ ] **Step 7: Run the full suite**

Same command block as Task 1 Step 7, with `weight_sync` included. Expected: all `OK`.

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/mayabridge/import_/convert/mesh.py tests/mayapy/weights_survive_skeleton.py
git commit -m "feat: import stores bone weights as mesh data

The .p3d format stores weights as named vertex selections and knows nothing about
skeletons. Import now keeps that form on the LOD transform in addition to building
a skinCluster, so a model opened without its rig still exports its weights.

The live skinCluster continues to win on export; this copy is the fallback."
```

---

## Self-review notes

**Spec coverage:** Stage 1 → Task 1 (sync point moved to scene save, which the spec left open). Stage 2 → Task 2. Stage 3 → Task 3. Stages 4–5 deliberately deferred to their own plan, as stated in the scope note.

**Deviation from the spec worth flagging:** the spec says "export synchronises weights from the live skin". This plan syncs on **scene save** instead, because writing to the scene during export violates the global constraint that export must not silently change the user's data. The dependency on the skeleton at export time is already removed by the existing fallback, so nothing is lost.

**Known risk:** Task 3's index mapping is the fiddly part — `vertex_map` runs Maya index → P3D source index, and the stored format needs Maya indices. Step 6 exists to catch the performance trap; the correctness trap is covered by Step 5's byte-identical check.
