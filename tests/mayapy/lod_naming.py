"""Assigning LOD status must not rename the user's mesh (run with mayapy).

Marking an existing mesh as a LOD used to rename it to the LOD's own name, so a mesh the
rigger called "helmet" came back as "Resolution_1". It reads tidy in the outliner and is
miserable to work with: the names you chose are gone, several LODs of one type end up as
Resolution_1/Resolution_2/..., and everything referring to the old name has to be redone.

A brand-new EMPTY LOD is the opposite case — it has no name worth keeping, so it still gets
the LOD name rather than `transform1`.

Run:  mayapy.exe tests/mayapy/lod_naming.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.actions.lod import _mark_selection_as_lod  # noqa: E402
from a3ob.ui.constants import LOD_DEFINITIONS  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def resolution_definition():
    return next(d for d in LOD_DEFINITIONS if d["has_resolution"])


def test_marking_a_mesh_keeps_its_name():
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    cmds.select(mesh, replace=True)

    node = _mark_selection_as_lod(resolution_definition(), 1)

    leaf = (node or "").split("|")[-1].split(":")[-1]
    check(leaf == "helmet", "the mesh must keep the name its author gave it, got %r" % (leaf,))
    check(cmds.objExists("helmet"), "helmet must still be in the scene under that name")
    check(cmds.getAttr("helmet.a3obIsLOD"), "it must still have been marked as a LOD")
    check(cmds.getAttr("helmet.a3obResolution") == 1, "with the resolution it was given")


def test_two_meshes_of_one_type_keep_their_own_names():
    """The rename also collided: mark two meshes as Resolution 1 and one gets suffixed."""
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)
    definition = resolution_definition()
    for name in ("helmet", "visor"):
        cmds.select(cmds.polyCube(name=name, ch=False)[0], replace=True)
        _mark_selection_as_lod(definition, 1)
    check(cmds.objExists("helmet") and cmds.objExists("visor"),
          "both meshes keep their own names, got %r" % (cmds.ls(type="transform"),))


def test_a_new_empty_lod_is_still_named_after_its_lod():
    """Nothing selected means nothing to preserve — an unnamed transform helps no one."""
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)
    cmds.select(clear=True)

    node = _mark_selection_as_lod(resolution_definition(), 2)

    leaf = (node or "").split("|")[-1].split(":")[-1]
    check(leaf == "Resolution_2", "a fresh empty LOD carries the LOD name, got %r" % (leaf,))


def main():
    test_marking_a_mesh_keeps_its_name()
    test_two_meshes_of_one_type_keep_their_own_names()
    test_a_new_empty_lod_is_still_named_after_its_lod()
    print("lod naming: OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
