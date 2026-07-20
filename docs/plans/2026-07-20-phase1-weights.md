# Phase 1: the skinCluster is the only source of truth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the duplicated weight store (`a3obBakedWeights` /
`a3obBakedWeightsPrevious`) so a mesh's weights live only in its `skinCluster`, and replace
the safety it provided with a validation warning.

**Architecture:** Weights are removed writer-first, reader-second, storage-last, so the
plugin works at every commit. The replacement safety net (an `a3obValidate` warning when a
skinned mesh has lost its rig) is built *before* the thing it replaces is removed, so no
commit leaves the user with neither.

**Tech Stack:** Python 3, Maya API 2.0 (`maya.api.OpenMaya`, `OpenMayaAnim`), `maya.cmds`,
`mayapy` for Maya-dependent tests, plain CPython for the schema test.

**Spec:** `docs/specs/2026-07-20-weights-live-skincluster-design.md`

## Prerequisite: the byte gate is vacuous in this worktree until you fix it

`Arma3ObjectBuilder-master/` (the `.p3d` fixtures) and `build/golden/` (the baseline) are
both gitignored, so `git worktree add` did not bring them. **They exist only in the main
repo.** Left alone, `tests/golden.py verify` prints `SKIP` and Task 5's critical assertion
proves nothing — a gate that looks green because it never ran.

Worse, the skip message reads `run: mayapy tests/golden.py capture`, which is the one
command that must never be run: it rewrites the baseline from current behaviour, so the
gate would thereafter approve whatever the code does. **Do not follow that message.**

Link them in before Task 1 (junctions, so nothing is copied and nothing diverges):

```bash
cmd //c mklink //J "Arma3ObjectBuilder-master" "C:\Users\targaryen\orca\Maya-ObjectBuilder\Arma3ObjectBuilder-master"
cmd //c mklink //J "build\golden" "C:\Users\targaryen\orca\Maya-ObjectBuilder\build\golden"
```

Then confirm the gate actually runs:

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```
Expected: real per-fixture output, **not** `SKIP`. If it still skips, stop — every byte
assertion in this plan is meaningless until it does not.

## Global Constraints

- **Never run `mayapy tests/golden.py capture`.** It overwrites the byte-gate baseline and
  makes the gate vacuous. Only `verify`. This holds even when a skip message suggests it.
- `mayapy` is `C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe` (override with
  `--mayapy`/`$MAYAPY`).
- Each mayapy test runs in its own process — `maya.standalone` cannot be initialised twice.
- A registered `MPxCommand` ignores code changes on plugin reload; the class keeps the
  session's first version. **Verify command changes under `mayapy`, not interactive Maya.**
- The repo has genuinely mixed line endings and no `.gitattributes`. Never rewrite a file
  wholesale; compare `git diff --shortstat` against `--ignore-cr-at-eol` before committing.
- Maya must be loading **this worktree** — see `2026-07-20-ui-simplification-index.md`
  Phase 0, including the stale main-repo `sys.path` entry, which matters here because this
  phase deletes modules.
- `tests/mayapy/*.py` are auto-discovered by `tests/run_all.py`; they use
  `_harness.bootstrap()`, `_harness.check(cond, msg)` and `_harness.REPO`.

## File Structure

| File | Responsibility after this phase |
|------|-------------------------------|
| `scripts/a3ob/mayabridge/weightsync.py` | **deleted** — its only job was the sync |
| `scripts/a3ob/mayabridge/skinquery.py` | skinCluster reads only; `store_bake` gone |
| `scripts/a3ob/mayabridge/commands/skin.py` | outlier selection only; bake/restore gone |
| `scripts/a3ob/mayabridge/export/taggs/skin.py` | live-skinCluster weights only |
| `scripts/a3ob/mayabridge/import_/convert/mesh.py` | no longer writes a bake |
| `scripts/a3ob/mayabridge/attributes.py` | two fewer schema entries |
| `scripts/a3ob/mayabridge/commands/validate.py` | gains the lost-rig warning |
| `scripts/a3ob/ui/panels/skinning.py` | no storage block |
| `scripts/a3ob/ui/entry.py` | no bake/restore wrappers |
| `plug-ins/MayaObjectBuilder.py` | no weightsync install/uninstall |

---

### Task 1: Re-verify the migration premise

The spec's "no migration needed" rests on a measurement taken on a scene that has since
changed. **If this task fails, stop and revise the spec** — the deprecation path comes back.

**Files:**
- Create: `tests/mayapy/weights_premise_check.py` (temporary; deleted in Task 10)

- [ ] **Step 1: Write the check**

```python
"""Every mesh carrying a bake must also have a live skinCluster (run with mayapy).

Phase 1 deletes a3obBakedWeights outright. That is only safe while no weight exists
ONLY as a bake. Point this at a real scene before deleting anything.

Run:  mayapy.exe tests/mayapy/weights_premise_check.py [scene.mb]
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def orphan_bakes():
    """LOD transforms with stored weights and no live skinCluster."""
    orphans = []
    for node in cmds.ls("*.a3obBakedWeights", objectsOnly=True, long=True) or []:
        if not (cmds.getAttr(node + ".a3obBakedWeights") or ""):
            continue
        shapes = cmds.listRelatives(node, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []
        live = shapes and cmds.ls(cmds.listHistory(shapes[0], pruneDagObjects=True) or [],
                                  type="skinCluster")
        if not live:
            orphans.append(node)
    return orphans


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else ""
    if scene:
        cmds.file(scene, open=True, force=True)
    orphans = orphan_bakes()
    _harness.check(
        not orphans,
        "these carry a bake with no live skinCluster, so the bake is their ONLY copy: %r"
        % (orphans,))
    print("OK - %d baked mesh(es), all with a live skinCluster"
          % len(cmds.ls("*.a3obBakedWeights", objectsOnly=True) or []))


main()
```

- [ ] **Step 2: Run it against the author's real scene**

Run:
```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_premise_check.py \
  "Z:/Projects/DayZ Projects/AB_Models_SXDIST/workspace/DeadCityGameplay/Clothing/Personal/Own_Dreykrus/Own_Dreykrus.mb"
```
Expected: `OK - 6 baked mesh(es), all with a live skinCluster`

**If any orphan is listed, stop.** Restore its rig, or reinstate the spec's deprecation
path (keep the schema entries and the export read path). Do not continue.

- [ ] **Step 3: Commit**

```bash
git add tests/mayapy/weights_premise_check.py
git commit -m "test: check no weight exists only as a bake before deleting the store"
```

---

### Task 2: `a3obValidate` warns when a skinned mesh has lost its rig

Built first: it is the replacement safety net, so it must exist before the bake goes.

**Files:**
- Modify: `scripts/a3ob/mayabridge/commands/validate.py`
- Create: `tests/mayapy/validate_lost_rig.py`

**Interfaces:**
- Produces: a `log.warn(name, "...")` row, so `a3obValidate` returns
  `"warning|<node>|mesh has bone selections but no skinCluster ..."`.

- [ ] **Step 1: Write the failing test**

```python
"""a3obValidate warns when a mesh carries bone selections but has no rig (run with mayapy).

This is the safety net that replaces a3obBakedWeights: instead of silently carrying a
second copy forever, say so the moment a rig goes missing.

Run:  mayapy.exe tests/mayapy/validate_lost_rig.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_rigged_lod():
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
    return transform, root


def rows_for(node):
    return [r for r in (cmds.a3obValidate() or []) if node in r]


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))

    transform, root = build_rigged_lod()
    lost = [r for r in rows_for(transform) if "no skinCluster" in r]
    _harness.check(not lost,
                   "a rigged mesh must not be warned about, got %r" % (lost,))

    cmds.delete(root)
    lost = [r for r in rows_for(transform) if "no skinCluster" in r]
    _harness.check(len(lost) == 1,
                   "expected exactly one lost-rig warning after deleting the "
                   "skeleton, got %r" % (lost,))
    _harness.check(lost[0].startswith("warning|"),
                   "lost rig is a warning, not an error: %r" % (lost[0],))
    print("OK - lost rig reported once, only when the rig is gone")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_lost_rig.py`
Expected: FAIL — `expected exactly one lost-rig warning after deleting the skeleton, got []`

- [ ] **Step 3: Implement the check**

In `scripts/a3ob/mayabridge/commands/validate.py`, inside `_validate_skin_weights`, replace
the body's opening so a missing rig is reported before outliers are attempted:

```python
    def _validate_skin_weights(self, mesh_path, name, log):
        """Flag vertices whose skin weights disagree with their neighbours — weight-transfer
        artefacts that stay invisible in bind pose but export as stray bone selections.

        Also flag a mesh whose rig is gone. Weights live only in the skinCluster now, and
        Maya deletes that with the joints, so a LOD that once had bone selections and now
        has no cluster will export with none — silently, unless this says so."""
        from a3ob.mayabridge.commands.skin import outliers_for_mesh
        from a3ob.mayabridge.skinquery import read_skin

        if read_skin(mesh_path) is None:
            log.warn(name, "mesh has no skinCluster — any bone selections it had are gone "
                           "with the rig and will not be exported")
            return

        try:
            outliers = outliers_for_mesh(mesh_path)
        except Exception as error:  # noqa: BLE001 - never let a skin read break validation
            log.warn(name, "could not read skin weights: %s" % error)
            return
        if outliers:
            log.warn(name, "%d skin weight outlier vertex(es) — a3obSkinWeights selects them; "
                           "fix with Skin > Smooth Skin Weights" % len(outliers))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/validate_lost_rig.py`
Expected: `OK - lost rig reported once, only when the rig is gone`

- [ ] **Step 5: Confirm static LODs are not spammed**

A Geometry LOD has no skinCluster and never had one, so it would now be warned about on
every validate. Run the existing suite to see whether that fires:

Run:
```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_weights_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```
Expected: PASS. If either fails with the new warning on an unrigged static mesh, narrow the
condition — only warn when the mesh's LOD type is one that carries bone selections, or when
sibling LODs in the same model are rigged. Re-run both tests after narrowing.

- [ ] **Step 6: Commit**

```bash
git add scripts/a3ob/mayabridge/commands/validate.py tests/mayapy/validate_lost_rig.py
git commit -m "feat: warn when a skinned mesh has lost its rig

The replacement for a3obBakedWeights. Rather than carrying a second copy of
every weight forever against a case that should not happen, say so the moment
it does."
```

---

### Task 3: Stop writing the bake on scene save

**Files:**
- Delete: `scripts/a3ob/mayabridge/weightsync.py`
- Modify: `plug-ins/MayaObjectBuilder.py:127-131` and `:144-148`
- Rewrite: `tests/mayapy/weight_sync.py`

- [ ] **Step 1: Rewrite the test to assert the opposite**

Replace the whole of `tests/mayapy/weight_sync.py`:

```python
"""Saving a scene writes no baked weights (run with mayapy).

Weights used to be mirrored into a3obBakedWeights on every save. The skinCluster is
the only store now, so a save must leave no such attribute behind.

Run:  mayapy.exe tests/mayapy/weight_sync.py
"""

import os
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build():
    cmds.file(new=True, force=True)
    transform = cmds.polyCylinder(name="synced", r=1, h=4, sx=8, sy=4, ch=False)[0]
    for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                       ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=name, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    transform = build()

    path = os.path.join(tempfile.mkdtemp(), "weights_on_save.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii")

    _harness.check(
        not cmds.attributeQuery("a3obBakedWeights", node=transform, exists=True),
        "saving must not write a3obBakedWeights")
    _harness.check(
        not cmds.attributeQuery("a3obBakedWeightsPrevious", node=transform, exists=True),
        "saving must not write a3obBakedWeightsPrevious")

    text = open(path, encoding="utf-8", errors="ignore").read()
    _harness.check("a3obBakedWeights" not in text,
                   "the saved .ma must contain no baked weights")

    import importlib
    try:
        importlib.import_module("a3ob.mayabridge.weightsync")
    except ImportError:
        pass
    else:
        _harness.check(False, "a3ob.mayabridge.weightsync should no longer exist")
    print("OK - a save writes no bake and weightsync is gone")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weight_sync.py`
Expected: FAIL — `saving must not write a3obBakedWeights`

- [ ] **Step 3: Delete the module and unwire it**

```bash
git rm scripts/a3ob/mayabridge/weightsync.py
```

In `plug-ins/MayaObjectBuilder.py`, delete the install block (around line 127):

```python
    try:
        from a3ob.mayabridge import weightsync
        weightsync.install()
    except Exception as error:  # noqa: BLE001
        om.MGlobal.displayWarning("weightsync install: %s" % error)
```

and the matching uninstall block (around line 144):

```python
    try:
        from a3ob.mayabridge import weightsync
        weightsync.uninstall()
    except Exception as error:  # noqa: BLE001
        om.MGlobal.displayWarning("weightsync uninstall: %s" % error)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weight_sync.py`
Expected: `OK - a save writes no bake and weightsync is gone`

- [ ] **Step 5: Confirm no callback leak on unload**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py`
Expected: PASS. This test covers callback removal on unload; with the save callback gone
there is one fewer to leak.

- [ ] **Step 6: Commit**

```bash
git add -A scripts/a3ob/mayabridge plug-ins/MayaObjectBuilder.py tests/mayapy/weight_sync.py
git commit -m "refactor: stop mirroring weights into an attribute on save

The skinCluster is the store now, so the sync had nothing left to keep current."
```

---

### Task 4: Stop writing the bake on import

**Files:**
- Modify: `scripts/a3ob/mayabridge/import_/convert/mesh.py:60`
- Create: `tests/mayapy/import_writes_no_bake.py`

- [ ] **Step 1: Write the failing test**

```python
"""Importing a P3D writes no baked-weight attribute (run with mayapy).

Import used to mirror bone selections into a3obBakedWeights. The skinCluster is the
only store now, and import does not create one, so it must write nothing.

Run:  mayapy.exe tests/mayapy/import_writes_no_bake.py
"""

import os
import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds

# The .p3d fixtures live in the gitignored reference clone, not in tests/ — the same
# path golden.py and p3d_workflow.py use. The character sample is the one that carries
# bone selections, which is what makes this test able to fail.
FIXTURE = os.path.join(_harness.REPO, "Arma3ObjectBuilder-master", "tests", "inputs",
                       "p3d", "sample_1_character.p3d")


def main():
    if not os.path.isfile(FIXTURE):
        print("SKIP - fixture absent (clone Arma3ObjectBuilder-master): %s" % FIXTURE)
        sys.exit(0)

    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.file(new=True, force=True)
    cmds.file(FIXTURE, i=True, type="Arma P3D", ignoreVersion=True,
              mergeNamespacesOnClash=False, options="")

    baked = cmds.ls("*.a3obBakedWeights", objectsOnly=True) or []
    _harness.check(not baked, "import must not write a3obBakedWeights, got %r" % (baked,))
    print("OK - character fixture imported, no baked weights written")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/import_writes_no_bake.py`
Expected: FAIL — `import must not write a3obBakedWeights, got [...]`

If it prints `SKIP`, the reference clone is missing:
`git clone https://github.com/MrClock8163/Arma3ObjectBuilder Arma3ObjectBuilder-master`.
It is gitignored format reference, not part of the repo.

If it *passes* immediately, the fixture carries no bone selections and the test proves
nothing — do not proceed on a green that cannot go red. Confirm the fixture is rigged by
checking that the import produced bone selection sets before continuing.

- [ ] **Step 3: Remove the write**

In `scripts/a3ob/mayabridge/import_/convert/mesh.py`, delete the line at 60 and the
`bone_rows` accumulation that feeds only it. Read the surrounding block first: if
`bone_rows` is used for nothing else, remove its construction too, rather than leaving a
list nobody consumes.

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/import_writes_no_bake.py`
Expected: `OK - import wrote no baked weights (...)`

- [ ] **Step 5: Confirm the import round-trip still holds**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/a3ob/mayabridge/import_/convert/mesh.py tests/mayapy/import_writes_no_bake.py
git commit -m "refactor: stop writing baked weights on import"
```

---

### Task 5: Drop the bake fallback from export

**Files:**
- Modify: `scripts/a3ob/mayabridge/export/taggs/skin.py` — remove
  `_add_baked_weight_taggs` and its call site
- Modify: `scripts/a3ob/mayabridge/export/taggs/__init__.py` if it re-exports the name

**Interfaces:**
- Consumes: nothing new.
- Produces: `_add_skin_weight_taggs(mesh_path, vertex_source_indices, lod)` remains the only
  weight writer.

- [ ] **Step 1: Run the byte gate first, to have a before**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify`
Expected: PASS. Record it — this is the reference point for Step 4.

- [ ] **Step 2: Find and remove the call site**

```bash
grep -rn "_add_baked_weight_taggs" scripts/
```

Delete the function from `export/taggs/skin.py`, its entry in that file's `__all__`, and
every call site the grep found.

- [ ] **Step 3: Verify the byte gate has not moved**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify`
Expected: PASS, identical to Step 1.

This is the critical assertion of the task: the golden fixture exports through a live
skinCluster, so removing the fallback must change nothing. **If it fails, the fixture was
relying on the bake** — stop, and reinstate the read path per the spec's rejected
deprecation route.

- [ ] **Step 4: Run the export suite**

Run: `python tests/run_all.py`
Expected: PASS except tests still referencing the removed names — those are handled in
Tasks 6-9. Note which fail; they must be the ones named there and no others.

- [ ] **Step 5: Commit**

```bash
git add scripts/a3ob/mayabridge/export/
git commit -m "refactor: export weights only from the live skinCluster

Byte gate verified unchanged before and after: the fixture exports through a
live cluster, so the fallback was never the path it took."
```

---

### Task 6: Remove `a3obBakeSkin`'s bake and restore

**This edits a hard contract** — CLAUDE.md pins registered command names and their flags.
`a3obBakeSkin` loses its reason to exist and is deregistered. That is safe here only because
the plugin has one user and no external scripts call it; record that in the commit message
so it never looks like drift.

**Files:**
- Modify: `scripts/a3ob/mayabridge/commands/skin.py` — remove `_bake`, `_restore`, the
  `-rs`/`-pv` flags, and the `BakeSkinCommand` class
- Modify: `scripts/a3ob/mayabridge/commands/__init__.py` — drop it from the registry
- Modify: `plug-ins/MayaObjectBuilder.py` — the command count in any comment or list
- Delete: `tests/mayapy/weights_restore.py`

- [ ] **Step 1: Write the failing test**

Add to a new `tests/mayapy/bake_command_gone.py`:

```python
"""a3obBakeSkin no longer exists; a3obSkinWeights still does (run with mayapy).

Deregistering a command is a deliberate break of the registered-name contract. This
pins the intent so a later reader sees a decision rather than an accident.

Run:  mayapy.exe tests/mayapy/bake_command_gone.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    _harness.check(not hasattr(cmds, "a3obBakeSkin"),
                   "a3obBakeSkin should be deregistered")
    _harness.check(hasattr(cmds, "a3obSkinWeights"),
                   "a3obSkinWeights must survive — it is the outlier selector")
    _harness.check(hasattr(cmds, "a3obTransferSkin"),
                   "a3obTransferSkin must survive")
    print("OK - bake command gone, the skin tools that matter remain")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/bake_command_gone.py`
Expected: FAIL — `a3obBakeSkin should be deregistered`

- [ ] **Step 3: Remove the command**

Delete `BakeSkinCommand` from `commands/skin.py` — its `syntax()` flags `-rs`/`-pv`, `_bake`
and `_restore` — and remove its registration entry. Keep `outliers_for_mesh`, which
`validate.py` (Task 2) and `a3obSkinWeights` both use.

```bash
git rm tests/mayapy/weights_restore.py
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/bake_command_gone.py`
Expected: `OK - bake command gone, the skin tools that matter remain`

- [ ] **Step 5: Verify registration still succeeds for everything else**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_correctness.py`
Expected: PASS. `initializePlugin` calls every `syntax()` up front (`_syntax_is_safe`); a
half-removed command surfaces here rather than at first dispatch, where a Python exception
in Maya's C++ callback kills the session.

- [ ] **Step 6: Commit**

```bash
git add -A scripts/a3ob/mayabridge/commands plug-ins/MayaObjectBuilder.py tests/mayapy/
git commit -m "refactor!: remove a3obBakeSkin

Deliberate edit to the registered-command contract, not drift. The command
existed to maintain a3obBakedWeights and its previous-copy swap; with the
skinCluster as the only store it has no remaining behaviour. Safe here because
the plugin has one user and nothing external calls it."
```

---

### Task 7: Remove `store_bake`

**Files:**
- Modify: `scripts/a3ob/mayabridge/skinquery.py` — remove `store_bake` and its `__all__`
  entry
- Modify: `scripts/a3ob/mayabridge/skinweights.py` — remove `bake_string`,
  `parse_bake_string` and `weights_from_bake` **only if** nothing else uses them

- [ ] **Step 1: Prove nothing still calls them**

```bash
grep -rn "store_bake\|bake_string\|parse_bake_string\|weights_from_bake" \
  scripts/ tests/ plug-ins/ install/ tools/
```
Expected after Tasks 3-6: no hits outside `skinquery.py` / `skinweights.py` themselves.
**Any remaining hit is a caller you have not handled** — resolve it before deleting.

- [ ] **Step 2: Delete what the grep proved unused**

Remove `store_bake` from `skinquery.py`. Remove from `skinweights.py` only the helpers the
grep showed to be unused; keep `MAX_INFLUENCES` and `MIN_ENCODABLE_WEIGHT`, which
`export/taggs/skin.py` imports as `sw.MAX_INFLUENCES` / `sw.MIN_ENCODABLE_WEIGHT`.

- [ ] **Step 3: Run the pure-Python suite**

Run: `python tests/run_all.py --only python`
Expected: PASS. This includes `py_compile` over every source file, which catches a name
removed while still referenced.

- [ ] **Step 4: Commit**

```bash
git add scripts/a3ob/mayabridge/
git commit -m "refactor: remove the bake string helpers, now unused"
```

---

### Task 8: Strip the storage block from the Skinning panel

**Files:**
- Modify: `scripts/a3ob/ui/panels/skinning.py` — remove `_weights_state`,
  `_weights_state_text`, `_why_nothing_restored`, the storage hint, `weights_state_label`,
  the Restore/Use-Older/Bake buttons, `run_bake_skin`, `run_restore_skin`,
  `_show_restore_previous`, `refresh_weights_state`
- Modify: `scripts/a3ob/ui/entry.py` — remove `_bake_skin_weights`,
  `_restore_skin_weights` and their `__all__` entries
- Modify: `scripts/a3ob/ui/dock.py:139` — the Skinning panel's `on_expand` becomes `None`
- Rewrite: `tests/mayapy/weights_panel_state.py`

- [ ] **Step 1: Rewrite the panel test**

Replace `tests/mayapy/weights_panel_state.py`:

```python
"""The Skinning panel holds no weight-storage UI (run with mayapy).

The storage model is gone, so the panel must not name it, and expanding the panel
must cost no scene scan — its on_expand callback existed only to refresh the state
line.

Run:  mayapy.exe tests/mayapy/weights_panel_state.py
"""

import inspect
import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    from a3ob.ui.panels import skinning

    source = inspect.getsource(skinning)
    for gone in ("a3obBakedWeights", "_weights_state", "run_bake_skin",
                 "run_restore_skin", "refresh_weights_state", "Restore Weights",
                 "Bake Now", "Use the Older Copy"):
        _harness.check(gone not in source,
                       "Skinning panel still references %r" % gone)

    for gone in ("_bake_skin_weights", "_restore_skin_weights"):
        from a3ob.ui import entry
        _harness.check(not hasattr(entry, gone),
                       "entry still exports %r" % gone)

    # Positive control: the panel must still hold the things that stay, or the checks
    # above would pass vacuously against an empty file.
    for kept in ("Transfer Skin from Body", "Test Pose", "influence_list"):
        _harness.check(kept in source, "Skinning panel lost %r" % kept)

    print("OK - storage UI gone, transfer/pose/influences intact")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_panel_state.py`
Expected: FAIL — `Skinning panel still references 'a3obBakedWeights'`

- [ ] **Step 3: Remove the storage block**

Delete from `scripts/a3ob/ui/panels/skinning.py` the module-level helpers
`_weights_state`, `_weights_state_text` and `_why_nothing_restored`; in
`_build_skinning_tab`, the `_hint("The mesh keeps its own copy of the weights...")` widget,
`self.weights_state_label`, and the whole `bake_row`; and the methods `run_bake_skin`,
`run_restore_skin`, `_show_restore_previous` and `refresh_weights_state`.

In `scripts/a3ob/ui/dock.py:139`, change:

```python
            ("Skinning", self._build_skinning_tab(), True, self.refresh_weights_state),
```

to:

```python
            ("Skinning", self._build_skinning_tab(), True, None),
```

In `scripts/a3ob/ui/entry.py`, remove `_bake_skin_weights` and `_restore_skin_weights` and
their two `__all__` entries.

- [ ] **Step 4: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_panel_state.py`
Expected: `OK - storage UI gone, transfer/pose/influences intact`

- [ ] **Step 5: Verify the dock still builds and stays quiet**

Run:
```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
```
Expected: PASS both.

- [ ] **Step 6: Commit**

```bash
git add scripts/a3ob/ui/ tests/mayapy/weights_panel_state.py
git commit -m "refactor: remove the weight-storage block from the Skinning panel

Takes the panel's only on_expand callback with it, so opening Skinning no
longer costs a scene scan."
```

---

### Task 9: Remove the schema entries

Deliberately last: everything reading these attributes is gone by now, so this cannot break
a caller.

- [ ] **Step 0: Sweep for readers this plan did not list**

```bash
grep -rn "BAKED_WEIGHTS\|a3obBakedWeights" scripts/ plug-ins/ install/ tools/ --include=*.py
```

Every surviving hit must be a file this task is about to edit. **This step exists because
the plan missed one.** `export/exporter.py`'s `_warn_about_missing_weights` read
`A.BAKED_WEIGHTS` to suppress its warning; it was in no task's file list, and deleting the
schema entry would have raised `AttributeError` on every export of a scene containing a
joint. Found by review during Task 5 and fixed in `e4e4a99`. Do not assume the list above
is complete — re-run the grep.

**Files:**
- Modify: `scripts/a3ob/mayabridge/attributes.py:35-39` — remove `BAKED_WEIGHTS` and
  `BAKED_WEIGHTS_PREVIOUS`
- Modify: `tests/python/test_attr_schema.py` — `GOLDEN` loses two rows

- [ ] **Step 1: Update the golden list first, so the test fails against the code**

In `tests/python/test_attr_schema.py`, delete these two rows from `GOLDEN`:

```python
    ("BAKED_WEIGHTS", "a3obBakedWeights", "a3bw"),
    ("BAKED_WEIGHTS_PREVIOUS", "a3obBakedWeightsPrevious", "a3bwp"),
```

Add above `GOLDEN`, so the count change reads as a decision:

```python
# 2026-07-20: BAKED_WEIGHTS and BAKED_WEIGHTS_PREVIOUS were removed deliberately, taking
# this list from 35 pairs to 33. The skinCluster is now the only place weights live —
# docs/specs/2026-07-20-weights-live-skincluster-design.md. Verified first that no mesh
# held a bake without a live cluster, so no scene lost data.
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/python/test_attr_schema.py -v`
Expected: FAIL — the golden list has 33 pairs, `attributes.py` still declares 35.

- [ ] **Step 3: Remove the two schema entries**

In `scripts/a3ob/mayabridge/attributes.py`, delete `BAKED_WEIGHTS`,
`BAKED_WEIGHTS_PREVIOUS` and the comment block between them (lines 35-39).

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/python/test_attr_schema.py -v`
Expected: PASS, 33 pairs.

- [ ] **Step 5: Commit**

```bash
git add scripts/a3ob/mayabridge/attributes.py tests/python/test_attr_schema.py
git commit -m "refactor!: drop the baked-weight attributes from the schema

35 pairs to 33. A deliberate edit to a hard contract: the schema exists to stop
an attribute silently ceasing to resolve in scenes holding data, and Task 1
verified no mesh holds a bake without a live skinCluster."
```

---

### Task 10: Gates and close-out

**Files:**
- Delete: `tests/mayapy/weights_premise_check.py`
- Rewrite: `tests/mayapy/weights_survive_skeleton.py`

- [ ] **Step 1: Repoint the survival test at the new behaviour**

Replace `tests/mayapy/weights_survive_skeleton.py` — it asserted weights outlive the rig,
which is exactly what no longer happens. It becomes the end-to-end statement of the new
contract:

```python
"""Deleting a rig loses its weights, and validation says so (run with mayapy).

The old promise was that weights survived losing the skeleton, paid for with a second
copy of every weight in every scene. The promise now is narrower and honest: they do
not survive, and you are told the moment they are gone.

Run:  mayapy.exe tests/mayapy/weights_survive_skeleton.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
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

    warned = [r for r in (cmds.a3obValidate() or [])
              if transform in r and "no skinCluster" in r]
    _harness.check(not warned, "a rigged mesh must not be warned about")

    cmds.delete(root)
    _harness.check(
        not cmds.ls(cmds.listHistory(transform, pruneDagObjects=True) or [],
                    type="skinCluster"),
        "deleting the skeleton must take the skinCluster with it")
    _harness.check(
        not cmds.attributeQuery("a3obBakedWeights", node=transform, exists=True),
        "no second copy should exist to fall back on")

    warned = [r for r in (cmds.a3obValidate() or [])
              if transform in r and "no skinCluster" in r]
    _harness.check(len(warned) == 1,
                   "losing the rig must be reported exactly once, got %r" % (warned,))
    print("OK - weights go with the rig, and validation says so")


main()
```

- [ ] **Step 2: Run it**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_survive_skeleton.py`
Expected: `OK - weights go with the rig, and validation says so`

- [ ] **Step 3: Drop the temporary premise check**

```bash
git rm tests/mayapy/weights_premise_check.py
```

Its job was to gate this phase, and the gate has been passed. `orphan_bakes()` is preserved
in the git history if it is ever needed again.

- [ ] **Step 4: Full suite**

Run: `python tests/run_all.py`
Expected: PASS, every test.

- [ ] **Step 5: Byte gate**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify`
Expected: PASS. **Never `capture`.**

- [ ] **Step 6: Line-ending check**

```bash
git diff --shortstat main..HEAD
git diff --shortstat --ignore-cr-at-eol main..HEAD
```
Expected: the two numbers agree. A large gap means a file was rewritten wholesale and its
line endings converted — find it and restore them before pushing.

- [ ] **Step 7: Commit and push**

```bash
git add -A tests/
git commit -m "test: weights go with the rig, and validation reports it

Replaces the survival test with the honest contract. Phase 1 complete: the
skinCluster is the only place weights live."
git push
```

- [ ] **Step 8: Tick Phase 1 in the PR**

Check the Phase 1 box in https://github.com/SXDIST/Maya-ObjectBuilder/pull/2 and note the
measured scene-size reduction in a comment.

---

## Self-review notes

**Spec coverage.** Write path (Tasks 3, 4), read path (Tasks 5, 6), storage (Tasks 7, 9),
UI (Task 8), the replacement warning (Task 2), the migration re-check (Task 1), and the
rewritten tests the spec names (Tasks 3, 8, 10) — `weight_sync`, `weights_restore`,
`weights_survive_skeleton`, `weights_panel_state` are each accounted for.

**Deliberately deferred to Phase 2.** The spec's "Consequences for the Auto LOD work"
section — duplicate, re-bind, `setWeights` — belongs to the generator refactor and is not
touched here.

**Not covered by any task, and not an oversight.** The spec mentions a dock action to strip
the two attributes from already-saved scenes so the 2.73 MB is reclaimed. It needs the
Preferences window from the Materials spec to have somewhere to live, so it is a Phase 3
item. Until then the attributes remain as inert data in existing scenes, harming nothing.
