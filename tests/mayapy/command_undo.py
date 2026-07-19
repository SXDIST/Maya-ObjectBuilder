"""Ctrl+Z must undo a3ob* commands (run with mayapy).

The commands wrote attributes straight through MPlug setters, which never enter Maya's undo
queue, so a mass assignment or a named property could not be taken back. They now route
their writes through an MDGModifier and declare themselves undoable.

Run:  mayapy.exe tests/mayapy/command_undo.py
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


def make_lod(name):
    transform = cmds.polyCube(name=name, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    return transform


def attr_or(transform, name, default):
    if not cmds.attributeQuery(name, node=transform, exists=True):
        return default
    return cmds.getAttr(transform + "." + name)


def test_set_mass_undo():
    transform = make_lod("undoMassLOD")
    cmds.select(transform, replace=True)

    before_has = attr_or(transform, "a3obHasMass", False)
    before_values = attr_or(transform, "a3obMassValues", "")

    cmds.a3obSetMass(value=2.5)

    after_values = attr_or(transform, "a3obMassValues", "")
    check(after_values and after_values != before_values,
          "the command must have written masses, got %r" % (after_values,))
    check(attr_or(transform, "a3obHasMass", False) is True, "a3obHasMass must be set")

    cmds.undo()

    check(attr_or(transform, "a3obMassValues", "") == before_values,
          "undo must restore a3obMassValues: %r -> %r"
          % (before_values, attr_or(transform, "a3obMassValues", "")))
    check(attr_or(transform, "a3obHasMass", False) == before_has,
          "undo must restore a3obHasMass")

    cmds.redo()
    check(attr_or(transform, "a3obMassValues", "") == after_values,
          "redo must reapply the masses")
    print("OK a3obSetMass is undoable (and redoable)")


def test_named_property_undo():
    transform = make_lod("undoPropLOD")
    cmds.select(transform, replace=True)

    before = attr_or(transform, "a3obProperties", "")
    cmds.a3obNamedProperty(setproperty="autocenter=0")
    after = attr_or(transform, "a3obProperties", "")
    check("autocenter" in after, "the property must be written, got %r" % (after,))

    cmds.undo()
    check(attr_or(transform, "a3obProperties", "") == before,
          "undo must restore a3obProperties: %r -> %r"
          % (before, attr_or(transform, "a3obProperties", "")))
    print("OK a3obNamedProperty is undoable")


def test_create_lod_undo():
    """CreateLOD MIXES the two undo mechanisms: it makes the node with cmds.createNode (which
    carries its own undo record) and writes the a3ob* attributes through the modifier. Undo
    must unwind both without leaving a half-built LOD behind."""
    cmds.select(clear=True)
    before = set(cmds.ls(type="transform") or [])

    result = cmds.a3obCreateLOD(lodType=0, resolution=1)
    created = set(cmds.ls(type="transform") or []) - before
    check(len(created) == 1, "expected exactly one new transform, got %r" % (created,))
    node = created.pop()
    check(cmds.getAttr(node + ".a3obIsLOD") is True, "new node must be marked as a LOD")

    cmds.undo()

    after = set(cmds.ls(type="transform") or [])
    check(node not in after,
          "undo must remove the transform created by a3obCreateLOD, %r survived" % node)
    check(after == before, "undo must leave the scene exactly as before")
    print("OK a3obCreateLOD undoes both the node and its attributes")


def test_update_proxy_undo():
    transform = make_lod("undoProxyLOD")
    cmds.addAttr(transform, longName="a3obIsProxy", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsProxy", True)
    cmds.select(transform, replace=True)

    cmds.a3obUpdateProxy(path="ca\dayz\proxy.p3d", index=3)
    check(attr_or(transform, "a3obProxyPath", "") != "", "proxy path must be written")

    cmds.undo()
    check(attr_or(transform, "a3obProxyPath", "") == "",
          "undo must clear the proxy path, got %r" % attr_or(transform, "a3obProxyPath", ""))
    print("OK a3obUpdateProxy is undoable")


def test_proxy_undo():
    """a3obProxy -fromSelection creates BOTH a placeholder transform AND a proxy selection
    objectSet (via cmds.sets, which never enters an MDagModifier). A prior version declared
    the command undoable and routed only the placeholder through self.modifier, so the
    objectSet survived Ctrl+Z as an orphan a3ob_proxy_* set — this must catch that."""
    transform = make_lod("undoProxyParent")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    cmds.select("%s.f[0]" % shape, replace=True)
    before_transforms = set(cmds.ls(type="transform") or [])
    before_sets = set(cmds.ls(type="objectSet") or [])

    cmds.a3obProxy(path="ca\dayz\p.p3d", index=1, fromSelection=True)
    created_transforms = set(cmds.ls(type="transform") or []) - before_transforms
    check(len(created_transforms) == 1, "expected one proxy transform, got %r" % (created_transforms,))
    created_sets = set(cmds.ls(type="objectSet") or []) - before_sets
    check(created_sets, "a3obProxy -fromSelection must create a proxy selection objectSet")
    proxy_sets = [name for name in created_sets if name.startswith("a3ob_proxy")]
    check(proxy_sets, "expected an a3ob_proxy_* objectSet, got %r" % (created_sets,))

    cmds.undo()
    survived_transforms = set(cmds.ls(type="transform") or []) - before_transforms
    check(not survived_transforms,
          "undo must remove the proxy transform, %r survived" % survived_transforms)
    survived_sets = set(cmds.ls(type="objectSet") or []) - before_sets
    check(not survived_sets,
          "undo must remove the proxy selection set, %r survived as an orphan" % survived_sets)
    print("OK a3obProxy undoes both its placeholder transform and its selection set")


def test_update_proxy_selection_set_undo():
    """a3obUpdateProxy's OTHER branch — renaming/re-tagging an EXISTING proxy selection set
    — had no coverage at all. It used to mix cmds.rename with modifier-less attr writes, so
    the rename undid but the a3obSelectionName/a3obIsProxySelection attribute writes did not."""
    transform = make_lod("undoUpdateProxySetLOD")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    cmds.select("%s.f[0]" % shape, replace=True)
    before_sets = set(cmds.ls(type="objectSet") or [])

    cmds.a3obProxy(path="ca\dayz\original.p3d", index=1, fromSelection=True)
    created_sets = set(cmds.ls(type="objectSet") or []) - before_sets
    check(len(created_sets) == 1, "expected exactly one proxy selection set, got %r" % (created_sets,))
    proxy_set = created_sets.pop()

    original_set_name = proxy_set
    original_selection_name = cmds.getAttr(proxy_set + ".a3obSelectionName")

    # noExpand: selecting a set by name normally selects its MEMBERS (that is how "quick
    # select sets" work), not the set node itself — a3obUpdateProxy needs the node.
    cmds.select(proxy_set, replace=True, noExpand=True)
    cmds.a3obUpdateProxy(path="ca\dayz\\updated.p3d", index=9)

    renamed_sets = set(cmds.ls(type="objectSet") or []) - before_sets
    check(len(renamed_sets) == 1, "expected the same single set after rename, got %r" % (renamed_sets,))
    renamed_set = renamed_sets.pop()
    check(renamed_set != original_set_name,
          "a3obUpdateProxy must have renamed the set, still %r" % renamed_set)
    updated_selection_name = cmds.getAttr(renamed_set + ".a3obSelectionName")
    check(updated_selection_name != original_selection_name,
          "a3obUpdateProxy must have changed a3obSelectionName, still %r" % updated_selection_name)

    cmds.undo()

    after_undo_sets = set(cmds.ls(type="objectSet") or []) - before_sets
    check(len(after_undo_sets) == 1, "expected the set to survive undo (just reverted), got %r" % (after_undo_sets,))
    reverted_set = after_undo_sets.pop()
    check(reverted_set == original_set_name,
          "undo must restore the original set name %r, got %r" % (original_set_name, reverted_set))
    check(cmds.getAttr(reverted_set + ".a3obSelectionName") == original_selection_name,
          "undo must restore a3obSelectionName: %r -> %r"
          % (original_selection_name, cmds.getAttr(reverted_set + ".a3obSelectionName")))
    print("OK a3obUpdateProxy undoes a rename+retag of an existing proxy selection set")


def test_set_flag_undo():
    """a3obSetFlag builds an objectSet. MFnSet.create() bypasses undo entirely, so the set
    used to survive Ctrl+Z."""
    transform = make_lod("undoFlagLOD")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    before = set(cmds.ls(type="objectSet") or [])

    cmds.select("%s.vtx[0:3]" % shape, replace=True)
    cmds.a3obSetFlag(component="vertex", value=1, name="a3ob_flagtest")
    created = set(cmds.ls(type="objectSet") or []) - before
    check(created, "a3obSetFlag must create an objectSet")

    cmds.undo()
    survived = set(cmds.ls(type="objectSet") or []) - before
    check(not survived, "undo must remove the flag set, %r survived" % survived)
    print("OK a3obSetFlag undoes its objectSet")


def test_find_components_undo():
    transform = make_lod("undoCompLOD")
    before = set(cmds.ls(type="objectSet") or [])

    cmds.select(transform, replace=True)
    cmds.a3obFindComponents()
    created = set(cmds.ls(type="objectSet") or []) - before
    check(created, "a3obFindComponents must create Component sets on a closed cube")

    cmds.undo()
    survived = set(cmds.ls(type="objectSet") or []) - before
    check(not survived, "undo must remove the component sets, %r survived" % survived)
    print("OK a3obFindComponents undoes its component sets")


def test_set_material_undo():
    transform = make_lod("undoMatLOD")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    before_sets = set(cmds.ls(type="objectSet") or [])
    before_shaders = set(cmds.ls(type="lambert") or [])

    cmds.select("%s.f[0]" % shape, replace=True)
    cmds.a3obSetMaterial(texture="ca\dayz\t_co.paa", material="ca\dayz\t.rvmat")
    check(set(cmds.ls(type="lambert") or []) - before_shaders, "a material must be created")

    cmds.undo()
    check(not (set(cmds.ls(type="lambert") or []) - before_shaders),
          "undo must remove the created material")
    check(not (set(cmds.ls(type="objectSet") or []) - before_sets),
          "undo must remove the created shading group")
    print("OK a3obSetMaterial undoes its shader and shading group")


def main():
    cmds.loadPlugin(os.path.join(_REPO, "plug-ins", "MayaObjectBuilder.py"))
    # mayapy starts with undo off; the queue is what this test is about.
    cmds.undoInfo(state=True, infinity=True)
    test_set_mass_undo()
    test_named_property_undo()
    test_create_lod_undo()
    test_update_proxy_undo()
    test_proxy_undo()
    test_update_proxy_selection_set_undo()
    test_set_flag_undo()
    test_find_components_undo()
    test_set_material_undo()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL command_undo: %s" % error, file=sys.stderr)
        raise
