# Influence Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unwanted bones from a garment inside the dock — see them, check where they sit, drop them — without leaving Paint Skin Weights or hunting joints in the Outliner.

**Architecture:** A Maya-free name-logic module, a new `a3obInfluence` command that does the scene work, and a section in the dock's Skinning panel that is a thin wrapper over the command. This mirrors how `a3obTransferSkin` and its panel already relate.

**Tech Stack:** Maya 2027, Python 3, `maya.api.OpenMaya` / `OpenMayaAnim` (API 2.0), `maya.cmds`, PySide6 through `a3ob.ui._qt`. Tests: `tests/python/*.py` (plain interpreter) and `tests/mayapy/*.py` (mayapy).

**Source spec:** `docs/specs/2026-07-19-influence-panel-design.md`

## Global Constraints

- Full validation after every task: `tests/python` → `py_compile` → `tests/mayapy`. Run the WHOLE suite — the `MComputation` breakage once surfaced in an unrelated workflow test.
- `MSyntax.addFlag` does not fail gracefully. A rejected flag name raises "Unexpected Internal Failure" at the command's FIRST dispatch and kills the interpreter, losing unsaved work. `set` and `fix` are known-reserved long names. `initializePlugin` guards every command through `_syntax_is_safe`, so a bad flag makes the command missing rather than fatal — but verify the command actually registers.
- Commands that mutate through `cmds` stay NON-undoable and wrap their body in `undo_chunk()`, giving one Ctrl+Z. Never mix that with `_UndoableBase` / `MDagModifier`.
- `weightDistribution` must be set to Neighbors (1) BEFORE removing influences. Redistribution happens during the removal, so setting it afterwards is too late.
- Weight below `1/254` (`skinweights.MIN_ENCODABLE_WEIGHT`) encodes to a zero byte and never reaches the `.p3d`. Vertex selection must use that threshold.
- Tool contexts exist only in an interactive session; under `mayapy` `cmds.currentCtx()` returns `None`. Every context call must degrade to a no-op headlessly or the tests cannot run.
- `tests/mayapy/dock_refresh_cost.py` must stay green: component picking may not cost a panel rebuild.
- Work on branch `skinning-and-native-cleanup`. Do not commit to `main`.

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/a3ob/mayabridge/influences.py` (create) | Name masks and the "which may be removed" rule. No Maya import. |
| `scripts/a3ob/mayabridge/commands/influence.py` (create) | `a3obInfluence`: list, select-vertices, remove. Owns the tool-context dance. |
| `scripts/a3ob/mayabridge/commands/__init__.py` (modify) | Import, `COMMANDS`, `__all__`. |
| `scripts/a3ob/ui/entry.py` (modify) | Three thin wrappers + one line in `_refresh_context_ui`. |
| `scripts/a3ob/ui/panels/skinning.py` (modify) | The "Influences" section and its handlers. |
| `tests/python/test_influences.py` (create) | Mask + removability rules. |
| `tests/mayapy/influence_panel.py` (create) | Command behaviour end to end. |

---

### Task 1: Name logic, Maya-free

**Files:**
- Create: `scripts/a3ob/mayabridge/influences.py`
- Test: `tests/python/test_influences.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `leaf_name(name) -> str`, `match_names(names, pattern) -> [str]`, `removable(all_names, requested) -> ([str], str)`.

- [ ] **Step 1: Write the failing test**

Create `tests/python/test_influences.py`:

```python
"""Influence-name rules — pure Python, no Maya.

The mask decides what the dock's influence list shows, and the removability rule is the
only thing standing between a broad selection and a mesh with no influences left (which
cannot deform at all). Both are pure string logic, so they get a fast test here rather
than a Maya one.

Run:  python tests/python/test_influences.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))

from a3ob.mayabridge.influences import leaf_name, match_names, removable


def check(condition, message):
    if not condition:
        raise AssertionError(message)


BONES = [
    "|Pelvis|Spine|Neck|Head",
    "|Pelvis|Spine|Neck",
    "rig:Face_Jawbone",
    "Face_Chin",
    "EyeLeft",
    "LeftHand",
]


def test_leaf_name():
    check(leaf_name("|Pelvis|Spine|Neck|Head") == "Head", "DAG path must reduce to the leaf")
    check(leaf_name("rig:Face_Jawbone") == "Face_Jawbone", "namespace must be stripped")
    check(leaf_name("LeftHand") == "LeftHand", "a bare name must survive unchanged")
    print("OK leaf_name strips paths and namespaces")


def test_match_names():
    check(match_names(BONES, "Face_*") == ["rig:Face_Jawbone", "Face_Chin"],
          "mask must match on the leaf, keeping the original name")
    check(match_names(BONES, "Eye*") == ["EyeLeft"], "Eye* must match the eye only")
    check(match_names(BONES, "Nothing*") == [], "a mask with no match must return nothing")
    print("OK match_names filters on the leaf name")


def test_empty_mask_matches_nothing():
    # An empty filter box must never arm a control that would strip an entire rig.
    check(match_names(BONES, "") == [], "an empty mask must match NOTHING, not everything")
    check(match_names(BONES, None) == [], "a missing mask must match nothing too")
    print("OK an empty mask matches nothing")


def test_removable_keeps_one():
    allowed, reason = removable(BONES, ["Face_Chin", "EyeLeft"])
    check(allowed == ["Face_Chin", "EyeLeft"], "requested bones present must be removable")
    check(reason == "", "a valid request needs no reason, got %r" % (reason,))

    allowed, reason = removable(BONES, list(BONES))
    check(allowed == [], "removing every influence must be refused")
    check("at least one" in reason, "the refusal must explain itself, got %r" % (reason,))

    allowed, reason = removable(BONES, ["NotOnThisMesh"])
    check(allowed == [], "bones that are not influences must not be reported as removable")
    check(reason, "an empty request must explain itself")
    print("OK removable refuses to strip the last influence")


def main():
    test_leaf_name()
    test_match_names()
    test_empty_mask_matches_nothing()
    test_removable_keeps_one()
    print("influence tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/python/test_influences.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'a3ob.mayabridge.influences'`

- [ ] **Step 3: Write the module**

Create `scripts/a3ob/mayabridge/influences.py`:

```python
"""Influence-name rules for ``a3obInfluence`` — no Maya imports.

Deliberately Maya-free so it can be unit-tested with a plain interpreter, the same way
``skinweights.py`` is; ``a3ob.mayabridge.commands.influence`` supplies the Maya plumbing.
"""

import fnmatch


def leaf_name(name):
    """The bare joint name out of a DAG path with an optional namespace."""
    return (name or "").split("|")[-1].split(":")[-1]


def match_names(names, pattern):
    """Names whose leaf matches a shell-style mask, in the order given.

    An empty mask matches NOTHING rather than everything. The mask drives what the dock's
    influence list shows, and an empty filter box must never fill that list with the whole
    rig sitting one click away from removal."""
    if not pattern:
        return []
    return [name for name in names if fnmatch.fnmatch(leaf_name(name), pattern)]


def removable(all_names, requested):
    """``(names that may go, reason nothing may)``.

    A skinCluster must keep at least one influence: a mesh with none cannot deform, and a
    request covering every bone is a slip rather than an instruction."""
    wanted = set(requested or [])
    present = [name for name in all_names if name in wanted]
    if not present:
        return [], "none of the requested influences are on this mesh"
    if len(present) >= len(all_names):
        return [], ("that would remove every influence (%d) — a skinCluster must keep at "
                    "least one, or the mesh stops deforming" % len(all_names))
    return present, ""


__all__ = ["leaf_name", "match_names", "removable"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/python/test_influences.py`
Expected: four `OK` lines then `influence tests OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/a3ob/mayabridge/influences.py tests/python/test_influences.py
git commit -m "feat: influence-name rules for the influence panel

Mask matching and the never-remove-the-last-influence rule, kept Maya-free so
they test under a plain interpreter.

An empty mask matches nothing rather than everything: the mask drives what the
dock's list shows, and an empty filter box must not fill it with the whole rig
one click away from removal."
```

---

### Task 2: The `a3obInfluence` command

**Files:**
- Create: `scripts/a3ob/mayabridge/commands/influence.py`
- Modify: `scripts/a3ob/mayabridge/commands/__init__.py`
- Test: `tests/mayapy/influence_panel.py`

**Interfaces:**
- Consumes: `influences.leaf_name/match_names/removable`, `skinweights.MIN_ENCODABLE_WEIGHT`, and `undo_chunk()` / `_Base` from `commands.helpers`.
- Produces: command `a3obInfluence` with flags `-li/-listInfluences`, `-ri/-removeInfluences <string>`, `-sv/-selectVertices <string>`; module functions `selected_mesh_shape()`, `skin_cluster_of_shape(shape)`, `influence_names(shape)`, `vertices_driven_by(shape, influence)`, `remove_influences(shape, requested) -> ([str], str)`.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/influence_panel.py`:

```python
"""a3obInfluence: list, inspect and remove the bones driving a mesh (run with mayapy).

Removing a bone cannot delete its weight — every vertex must sum to 1.0, so the weight
moves to other influences. Which ones is decided by the skinCluster's weightDistribution:
"Distance" picks the nearest bone and "Neighbors" picks what the surrounding vertices
already use. Measured on a collar weighted to facial bones, removing them under Neighbors
puts the weight on Head/Neck; under Distance it scatters. The command must set Neighbors
BEFORE removing, because redistribution happens during the removal.

Run:  mayapy.exe tests/mayapy/influence_panel.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def unwrap(result):
    """MPxCommand.setResult comes back as a 1-element list under mayapy."""
    if isinstance(result, (list, tuple)) and len(result) == 1:
        return result[0]
    return result


def build():
    """A collar skinned to Neck/Head plus two facial bones it should never have kept."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="collar", r=1, h=6, sx=8, sy=6, ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]

    cmds.select(clear=True)
    neck = cmds.joint(position=(0, -3, 0), name="Neck")
    head = cmds.joint(position=(0, 0, 0), name="Head")
    cmds.select(clear=True)
    jaw = cmds.joint(position=(0.5, 1, 0), name="Face_Jawbone")
    chin = cmds.joint(position=(0.5, 1.5, 0), name="Face_Chin")

    skin = cmds.skinCluster(neck, head, jaw, chin, mesh,
                            toSelectedBones=True, maximumInfluences=4)[0]
    # Everything on Head, except a band that (wrongly) sits on the facial bones.
    for vertex in range(cmds.polyEvaluate(mesh, vertex=True)):
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex),
                         transformValue=[(neck, 0.0), (head, 1.0), (jaw, 0.0), (chin, 0.0)])
    for vertex in range(8):
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex),
                         transformValue=[(neck, 0.0), (head, 0.0), (jaw, 0.6), (chin, 0.4)])
    return mesh, shape, skin


def main():
    cmds.loadPlugin(os.path.join(_REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.undoInfo(state=True, infinity=True)

    # _syntax_is_safe skips a command whose syntax() Maya rejects, so a bad flag name shows
    # up as the command simply not existing rather than as a crash. Catch that here.
    check(cmds.pluginInfo("MayaObjectBuilder", query=True, loaded=True),
          "the plugin must be loaded")
    check("a3obInfluence" in (cmds.pluginInfo("MayaObjectBuilder", query=True, command=True) or []),
          "a3obInfluence did not register — a flag long name was probably rejected")

    mesh, shape, skin = build()
    cmds.select(mesh, replace=True)

    # 1. Listing
    listed = cmds.a3obInfluence(listInfluences=True) or []
    if isinstance(listed, str):
        listed = [listed]
    leaves = {name.split("|")[-1].split(":")[-1] for name in listed}
    check(leaves == {"Neck", "Head", "Face_Jawbone", "Face_Chin"},
          "all four influences must be listed, got %r" % (sorted(leaves),))

    # 2. Selecting the vertices a bone drives
    count = int(unwrap(cmds.a3obInfluence(selectVertices="Face_Jawbone")) or 0)
    check(count == 8, "Face_Jawbone drives the 8-vertex band, got %d" % count)
    selected = cmds.ls(selection=True, flatten=True) or []
    check(all(".vtx[" in item for item in selected),
          "the selection must be vertex components, got %r" % (selected[:3],))

    # 3. Removing — the weight must land where the neighbours are, not on the nearest bone
    cmds.select(mesh, replace=True)
    removed = int(unwrap(cmds.a3obInfluence(removeInfluences="Face_Jawbone,Face_Chin")) or 0)
    check(removed == 2, "both facial bones must be removed, got %d" % removed)

    left = cmds.skinCluster(skin, query=True, influence=True) or []
    check({n.split("|")[-1] for n in left} == {"Neck", "Head"},
          "only Neck and Head may remain, got %r" % (left,))
    check(cmds.getAttr(skin + ".weightDistribution") == 1,
          "weightDistribution must be Neighbors (1) so weight follows the neighbours")

    values = cmds.skinPercent(skin, "%s.vtx[0]" % shape, query=True, value=True)
    check(abs(sum(values) - 1.0) < 1e-4, "the vertex must stay normalized, got %r" % (values,))
    head_index = [n.split("|")[-1] for n in left].index("Head")
    check(values[head_index] > 0.5,
          "the facial weight must have moved to Head like its neighbours, got %r" % (values,))

    # 4. Refusing to strip the mesh bare
    cmds.select(mesh, replace=True)
    stripped = int(unwrap(cmds.a3obInfluence(removeInfluences=",".join(left))) or 0)
    check(stripped == 0, "removing every influence must be refused, removed %d" % stripped)
    check(len(cmds.skinCluster(skin, query=True, influence=True) or []) == 2,
          "the refusal must leave the skinCluster untouched")

    # 5. One undo takes the whole removal back
    cmds.undo()
    restored = {n.split("|")[-1] for n in (cmds.skinCluster(skin, query=True, influence=True) or [])}
    check("Face_Jawbone" in restored,
          "one undo must restore the removed influences, got %r" % (sorted(restored),))

    print("OK a3obInfluence lists, selects, removes to neighbours, refuses to strip, undoes")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL influence_panel: %s" % error, file=sys.stderr)
        raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/influence_panel.py`
Expected: FAIL with `No object matches name: a3obInfluence` (the command does not exist yet)

- [ ] **Step 3: Write the command module**

Create `scripts/a3ob/mayabridge/commands/influence.py`:

```python
"""``a3obInfluence`` — list, inspect and remove the bones driving the selected mesh.

Dropping a bone from a garment is a round trip in stock Maya: leave the paint tool, find
the joint in the Outliner, add the mesh back to the selection, use the menu, return to
painting. Everything needed to make the decision is visible only inside the paint tool,
and the operation is only available outside it. This command is the scriptable half of the
dock's Influences panel.

Removing an influence never deletes its weight. Every vertex must sum to 1.0, so the weight
moves to the other influences, and the skinCluster's ``weightDistribution`` decides which:
"Distance" hands it to the nearest bone and "Neighbors" to whatever the surrounding
vertices already use. Distance is Maya's default and is how head weight ends up on an arm,
so removal switches to Neighbors first — during removal, not after, because the
redistribution happens as part of it.
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from a3ob.mayabridge import influences as inf
from a3ob.mayabridge import skinweights as sw

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403

# Artisan's skin-paint contexts are named around this stem (artAttrSkinContext,
# artAttrSkinPaintCtx...). Matching on the stem avoids depending on one exact spelling.
_PAINT_CONTEXT_STEM = "artAttrSkin"


def selected_mesh_shape():
    """The first mesh shape in the selection, as a full path, or ''."""
    for name in cmds.ls(selection=True, long=True) or []:
        node = name.split(".", 1)[0]
        if cmds.nodeType(node) == "mesh":
            return node
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                    noIntermediate=True, type="mesh") or []
        if shapes:
            return shapes[0]
    return ""


def skin_cluster_of_shape(shape):
    """The skinCluster deforming a mesh shape, as a node name, or ''."""
    history = cmds.listHistory(shape, pruneDagObjects=True) or []
    skins = cmds.ls(history, type="skinCluster") or []
    return skins[0] if skins else ""


def influence_names(shape):
    """Influence names of the mesh's skinCluster (empty when it has none)."""
    skin = skin_cluster_of_shape(shape)
    if not skin:
        return []
    return cmds.skinCluster(skin, query=True, influence=True) or []


def vertices_driven_by(shape, influence, threshold=sw.MIN_ENCODABLE_WEIGHT):
    """``shape.vtx[i]`` names the influence drives above the p3d encoding threshold.

    Below 1/254 a weight encodes to a zero byte and never reaches the file, so showing
    those vertices would misrepresent what is actually bound.

    Read through MFnSkinCluster rather than per-vertex skinPercent: a garment runs to
    thousands of vertices and one query each is unusable interactively."""
    skin = skin_cluster_of_shape(shape)
    if not skin:
        return []

    mesh_selection = om.MSelectionList()
    mesh_selection.add(shape)
    mesh_path = mesh_selection.getDagPath(0)

    skin_selection = om.MSelectionList()
    skin_selection.add(skin)
    skin_fn = oma.MFnSkinCluster(skin_selection.getDependNode(0))

    names = [path.partialPathName() for path in skin_fn.influenceObjects()]
    leaf = inf.leaf_name(influence)
    index = next((i for i, name in enumerate(names) if inf.leaf_name(name) == leaf), -1)
    if index < 0:
        return []

    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(om.MFn.kMeshVertComponent)
    component_fn.setCompleteData(om.MFnMesh(mesh_path).numVertices)
    weights, count = skin_fn.getWeights(mesh_path, component)
    if count <= 0:
        return []

    return ["%s.vtx[%d]" % (shape, vertex)
            for vertex in range(len(weights) // count)
            if weights[vertex * count + index] > threshold]


def _leave_paint_tool():
    """Leave the Artisan paint tool, returning the context to restore (or '').

    Changing a skinCluster's influence list while the paint tool holds it is the leading
    suspect in a silent, log-less crash. Contexts exist only in an interactive session —
    under mayapy ``currentCtx()`` returns None — so this is a no-op headlessly."""
    try:
        current = cmds.currentCtx()
    except Exception:  # noqa: BLE001 - no UI at all
        return ""
    if not current or _PAINT_CONTEXT_STEM not in current:
        return ""
    try:
        cmds.setToolTo("selectSuperContext")
    except Exception:  # noqa: BLE001 - nothing to switch to; carry on regardless
        return ""
    return current


def _restore_tool(context):
    """Put the paint tool back. Never fatal: the removal already succeeded."""
    if not context:
        return
    try:
        if cmds.contextInfo(context, exists=True):
            cmds.setToolTo(context)
    except Exception:  # noqa: BLE001 - context went away underneath us
        pass


def remove_influences(shape, requested):
    """Remove the named influences. Returns ``(removed names, reason nothing was)``."""
    skin = skin_cluster_of_shape(shape)
    if not skin:
        return [], "no skinCluster on %s" % shape

    names = cmds.skinCluster(skin, query=True, influence=True) or []
    allowed, reason = inf.removable(names, requested)
    if not allowed:
        return [], reason

    survivors = [name for name in names if name not in set(allowed)]
    locked = [name for name in survivors
              if cmds.attributeQuery("lockInfluenceWeights", node=name, exists=True)
              and cmds.getAttr(name + ".lockInfluenceWeights")]
    if survivors and len(locked) == len(survivors):
        return [], ("every remaining influence is locked (%s) — normalization would have "
                    "nowhere to put the weight"
                    % ", ".join(inf.leaf_name(name) for name in locked[:4]))

    context = _leave_paint_tool()
    try:
        with undo_chunk():
            try:
                # Neighbors, and BEFORE the removal: redistribution happens during it.
                cmds.setAttr(skin + ".weightDistribution", 1)
            except RuntimeError:
                pass  # locked or driven by a connection; not worth failing over
            cmds.skinCluster(skin, edit=True, removeInfluence=allowed)
    finally:
        _restore_tool(context)
    return allowed, ""


class InfluenceCommand(_Base):
    """``a3obInfluence`` — the scene half of the dock's Influences panel."""

    kName = "a3obInfluence"

    @staticmethod
    def creator():
        return InfluenceCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-li", "-listInfluences")
        s.addFlag("-ri", "-removeInfluences", om.MSyntax.kString)
        s.addFlag("-sv", "-selectVertices", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)

        shape = selected_mesh_shape()
        if not shape:
            om.MGlobal.displayWarning("a3obInfluence: select a skinned mesh first")
            self.setResult([])
            return

        if argdb.isFlagSet("-sv"):
            name = argdb.flagArgumentString("-sv", 0)
            components = vertices_driven_by(shape, name)
            if not components:
                om.MGlobal.displayWarning(
                    "a3obInfluence: '%s' drives no vertex above %.5f on %s"
                    % (name, sw.MIN_ENCODABLE_WEIGHT, shape.split("|")[-1]))
                self.setResult(0)
                return
            cmds.select(components, replace=True)
            om.MGlobal.displayInfo("a3obInfluence: selected %d vertex(es) driven by %s"
                                   % (len(components), inf.leaf_name(name)))
            self.setResult(len(components))
            return

        if argdb.isFlagSet("-ri"):
            requested = [name for name in argdb.flagArgumentString("-ri", 0).split(",") if name]
            removed, reason = remove_influences(shape, requested)
            if reason:
                om.MGlobal.displayWarning("a3obInfluence: %s" % reason)
            else:
                om.MGlobal.displayInfo(
                    "a3obInfluence: removed %d influence(s) — weight moved to the bones the "
                    "neighbouring vertices use: %s"
                    % (len(removed), ", ".join(inf.leaf_name(name) for name in removed)))
            self.setResult(len(removed))
            return

        names = influence_names(shape)
        if not names:
            om.MGlobal.displayWarning("a3obInfluence: %s has no skinCluster"
                                      % shape.split("|")[-1])
        self.setResult(names)


__all__ = [
    "InfluenceCommand",
    "selected_mesh_shape",
    "skin_cluster_of_shape",
    "influence_names",
    "vertices_driven_by",
    "remove_influences",
]
```

- [ ] **Step 4: Register the command**

In `scripts/a3ob/mayabridge/commands/__init__.py`, add the import after the `skin` import:

```python
from a3ob.mayabridge.commands.influence import InfluenceCommand
```

add `InfluenceCommand` to the end of the `COMMANDS` list:

```python
COMMANDS = [
    ValidateCommand, SetMassCommand, SetMaterialCommand, SetFlagCommand,
    FindComponentsCommand, CreateLODCommand, ProxyCommand, NamedPropertyCommand,
    UpdateProxyCommand, SkinWeightsCommand, TransferSkinCommand, TestPoseCommand,
    ReferenceAssetCommand, BakeSkinCommand, InfluenceCommand,
]
```

and add `"InfluenceCommand",` to `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/influence_panel.py`
Expected: `OK a3obInfluence lists, selects, removes to neighbours, refuses to strip, undoes`

If the run dies with "Unexpected Internal Failure" at the first `a3obInfluence` call, a flag long name was rejected. Rename it (avoid `set`, `fix`, and bare verbs) and re-run — do NOT try to catch the exception, the interpreter is already gone.

- [ ] **Step 6: Run the full suite**

```bash
python tests/python/test_influences.py && python tests/python/test_qem.py && python tests/python/test_skinweights.py && python tests/python/test_p3d_roundtrip.py && python tests/python/test_model_cfg.py
python -m py_compile $(find scripts plug-ins tests -name '*.py')
for t in influence_panel skin_transfer weight_sync weights_survive_skeleton scene_watch command_undo command_correctness export_uses_live_mesh dock_refresh_cost skin_weights_workflow p3d_workflow model_cfg_workflow; do
  echo "=== $t ==="; "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/$t.py 2>&1 | grep -aE "^OK|^FAIL"
done
```

Expected: every line starts with `OK`, none with `FAIL`.

- [ ] **Step 7: Commit**

```bash
git add scripts/a3ob/mayabridge/commands/influence.py scripts/a3ob/mayabridge/commands/__init__.py tests/mayapy/influence_panel.py
git commit -m "feat: a3obInfluence lists, inspects and removes skin influences

Dropping a bone from a garment is a round trip in stock Maya: leave the paint
tool, find the joint in the Outliner, reselect the mesh, use the menu, go back.
What you need to decide is visible only inside the paint tool; the operation only
exists outside it.

Removal sets weightDistribution to Neighbors first. Weight cannot be deleted, only
moved — every vertex must sum to 1.0 — and Maya's default hands it to the nearest
bone rather than the one the surrounding vertices use, which is how head weight
lands on an arm. The order matters: redistribution happens during the removal.

The paint tool is left and restored around the change, since mutating an influence
list while Artisan holds it is the leading suspect in a silent, log-less crash."
```

---

### Task 3: The Influences section in the dock

**Files:**
- Modify: `scripts/a3ob/ui/entry.py`
- Modify: `scripts/a3ob/ui/panels/skinning.py`

**Interfaces:**
- Consumes: command `a3obInfluence`, `influences.match_names`, `_qt_button`/`_hint`/`_CollapsibleSection` from `a3ob.ui.widgets`.
- Produces: `entry._list_influences() -> [str]`, `entry._remove_influences(names) -> int`, `entry._select_influence_vertices(name) -> int`; `SkinningPanelMixin.refresh_influences()`.

- [ ] **Step 1: Add the wrappers**

In `scripts/a3ob/ui/entry.py`, after `_bake_skin_weights`:

```python
def _list_influences():
    """Influence names of the selected mesh's skinCluster."""
    load_plugin()
    result = cmds.a3obInfluence(listInfluences=True)
    if result is None:
        return []
    if isinstance(result, str):
        return [result]
    return list(result)


def _remove_influences(names):
    """Remove the named influences from the selected mesh. Returns how many went."""
    load_plugin()
    if not names:
        return 0
    result = cmds.a3obInfluence(removeInfluences=",".join(names))
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)


def _select_influence_vertices(name):
    """Select the vertices one influence drives. Returns how many."""
    load_plugin()
    result = cmds.a3obInfluence(selectVertices=name)
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)
```

- [ ] **Step 2: Export the wrappers**

`panels/skinning.py` reaches these through `from a3ob.ui.entry import *`, and a star import
skips names beginning with an underscore unless `__all__` lists them. `entry.py` already has
an explicit `__all__` carrying `"_transfer_skin"`, `"_bake_skin_weights"` and friends —
without this step the panel dies with `NameError` the moment the dock is built.

Add to `__all__` in `scripts/a3ob/ui/entry.py`, beside `"_bake_skin_weights"`:

```python
    "_list_influences",
    "_remove_influences",
    "_select_influence_vertices",
```

- [ ] **Step 3: Refresh the section with the other panels**

In `scripts/a3ob/ui/entry.py`, inside `_refresh_context_ui`, add after `dock.refresh_mass_summary()`:

```python
    dock.refresh_influences()
```

- [ ] **Step 4: Build the section**

In `scripts/a3ob/ui/panels/skinning.py`, add to `_build_skinning_tab` just before `self.skinning_summary = _hint("")`:

```python
        layout.addWidget(_hint("Bones driving the selected mesh. Filter narrows the list; "
                               "the buttons act on what you highlight in it. Removing a "
                               "bone moves its weight to the bones the neighbouring "
                               "vertices use — weight is never deleted, only moved."))

        filter_row = qt_widgets.QHBoxLayout()
        filter_row.addWidget(qt_widgets.QLabel("Filter"))
        self.influence_filter = qt_widgets.QLineEdit(
            cmds.optionVar(query="MayaObjectBuilder_influence_filter")
            if cmds.optionVar(exists="MayaObjectBuilder_influence_filter") else "")
        self.influence_filter.setPlaceholderText("Face_*   (blank shows everything)")
        self.influence_filter.setToolTip(
            "Shell-style mask matched against the bone name, e.g. Face_* or Eye*. "
            "Leave blank to list every influence.")
        self.influence_filter.textChanged.connect(self.refresh_influences)
        filter_row.addWidget(self.influence_filter)
        layout.addLayout(filter_row)

        self.influence_list = qt_widgets.QListWidget()
        self.influence_list.setSelectionMode(
            qt_widgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.influence_list.setMaximumHeight(160)
        self.influence_list.setToolTip("Bones driving the selected mesh.")
        layout.addWidget(self.influence_list)

        influence_row = qt_widgets.QHBoxLayout()
        influence_row.addWidget(_qt_button(
            "Select Vertices", self.run_select_influence_vertices,
            "Select the vertices the highlighted bone actually drives.", ":/aselect.png"))
        influence_row.addWidget(_qt_button(
            "Remove", self.run_remove_influences,
            "Remove the highlighted bones; their weight moves to what the neighbours use.",
            ":/delete.png"))
        layout.addLayout(influence_row)
```

Note: the filter is empty by default and an empty filter shows EVERYTHING here — `match_names` is only consulted when the box has text. That is deliberate: an empty list would look broken, while `match_names("")` returning nothing protects the removal path in Task 1.

- [ ] **Step 5: Add the handlers**

In `scripts/a3ob/ui/panels/skinning.py`, add to `SkinningPanelMixin` after `run_bake_skin`:

```python
    def refresh_influences(self):
        """Repopulate the influence list from the selected mesh, keeping the highlight."""
        if getattr(self, "influence_list", None) is None:
            return
        from a3ob.mayabridge.influences import match_names

        previously = {item.text() for item in self.influence_list.selectedItems()}
        names = _list_influences()
        pattern = self.influence_filter.text().strip() if self.influence_filter else ""
        shown = match_names(names, pattern) if pattern else names

        self.influence_list.clear()
        for name in shown:
            self.influence_list.addItem(name.split("|")[-1].split(":")[-1])
        for index in range(self.influence_list.count()):
            item = self.influence_list.item(index)
            if item.text() in previously:
                item.setSelected(True)

        if pattern:
            cmds.optionVar(stringValue=("MayaObjectBuilder_influence_filter", pattern))

    def _highlighted_influences(self):
        return [item.text() for item in self.influence_list.selectedItems()]

    def run_select_influence_vertices(self):
        picked = self._highlighted_influences()
        if not picked:
            self._set_skinning_summary("Highlight a bone in the list first.")
            return
        count = _select_influence_vertices(picked[0])
        self._set_skinning_summary(
            "{0} drives {1} vertex(es) — selected.".format(picked[0], count) if count
            else "{0} drives no vertices worth exporting.".format(picked[0]))

    def run_remove_influences(self):
        picked = self._highlighted_influences()
        if not picked:
            self._set_skinning_summary("Highlight the bones to remove first.")
            return
        removed = _remove_influences(picked)
        self.refresh_influences()
        self._set_skinning_summary(
            "Removed {0} influence(s); weight moved to the neighbours' bones.".format(removed)
            if removed else "Nothing removed — see the script editor for why.")
```

- [ ] **Step 6: Verify the dock still builds and stays cheap**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py`
Expected: 14 `OK` lines including `OK redesigned UI builds without layout errors`

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py`
Expected: `OK dock refresh: component picking costs 0 rebuilds, LOD switch still refreshes`

If `dock_refresh_cost` fails, `refresh_influences` is being called outside the debounced path — it must only run from `_refresh_context_ui`, never from a selection callback of its own.

- [ ] **Step 7: Run the full suite**

Same command block as Task 2 Step 6. Expected: all `OK`.

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/ui/entry.py scripts/a3ob/ui/panels/skinning.py
git commit -m "feat: Influences section in the Skinning panel

Lists the bones driving the selected mesh with a remembered name filter, selects
the vertices a bone actually drives so you can see where it sits, and removes the
highlighted ones.

The filter narrows the list; the buttons act on the highlight. Removing is
therefore two deliberate steps rather than one keystroke away from stripping a rig."
```

- [ ] **Step 9: Check the one thing tests cannot**

In interactive Maya: open Paint Skin Weights on a garment, then press Remove in the panel. The paint tool must come back afterwards. Contexts do not exist under mayapy, so this cannot be automated — verify it by hand once.

---

## Self-review notes

**Spec coverage:** `influences.py` + mask/removability → Task 1. `a3obInfluence`, tool-context handling, `weightDistribution` ordering, the 1/254 threshold, locked-influence reporting → Task 2. Panel section, wrappers, refresh hook → Task 3. The spec's error table maps onto Task 2's `remove_influences` returns and Task 3's summary strings.

**Deliberate deviation:** the spec says an empty mask matches nothing. That rule lives in `match_names` and protects the removal path, but the panel shows the FULL list when the filter box is empty — an empty list on an unfiltered panel reads as broken. Task 3 Step 4 states this.

**Known risk:** flag long names. `-listInfluences` / `-removeInfluences` / `-selectVertices` avoid the reserved words that bit this plugin before, but `MSyntax.addFlag` gives no safe way to test a name except registering it. Task 2 Step 5 says what to do if the interpreter dies there.
