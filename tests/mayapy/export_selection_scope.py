"""Exporting a selected GROUP exports the LODs under it (run with mayapy).

`_resolve_lod_path` only ever walked the DAG upward — from a mesh to the LOD transform above
it. Selecting the folder that holds a model's LODs therefore resolved to nothing and export
failed with "selection does not contain an Object Builder LOD", which is also what a plain
Maya group named "geometries" produced when it was mistaken for a Geometry LOD.

That matters most with several models in one scene bound for separate .p3d files: a folder
per model is the obvious way to organise them, and it was the one thing that could not be
exported.

Run:  mayapy.exe tests/mayapy/export_selection_scope.py
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

from a3ob.formats.p3d import MLOD  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_lod(name, resolution, parent=None, with_mesh=True):
    if with_mesh:
        transform = cmds.polyCube(name=name, ch=False)[0]
    else:
        transform = cmds.createNode("transform", name=name)
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    cmds.setAttr(transform + ".a3obResolution", resolution)
    if parent:
        transform = cmds.parent(transform, parent)[0]
    return cmds.ls(transform, long=True)[0]


def export_selected(name):
    path = os.path.join(tempfile.gettempdir(), name)
    cmds.file(path, force=True, options="selectedOnly=1", type="Arma P3D", exportSelected=True)
    return path


def new_scene():
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)


def test_selecting_the_group_exports_the_lods_under_it():
    new_scene()
    helmet = cmds.createNode("transform", name="Own_Helmet")
    make_lod("Resolution_0", 0, parent=helmet)
    make_lod("Resolution_1", 1, parent=helmet)
    # A second model in the same scene must stay out of this file.
    other = cmds.createNode("transform", name="Own_Vest")
    make_lod("Vest_Resolution_0", 0, parent=other)

    cmds.select(helmet, replace=True)
    written = export_selected("a3ob_group_scope.p3d")
    check(os.path.exists(written), "the export must produce a file")

    mlod = MLOD.read_file(written)
    check(len(mlod.lods) == 2,
          "both LODs under the selected group, and only those, got %d" % len(mlod.lods))


def test_nested_groups_are_followed():
    new_scene()
    root = cmds.createNode("transform", name="Own_Helmet")
    visuals = cmds.createNode("transform", name="visuals", parent=root)
    make_lod("Resolution_0", 0, parent=visuals)
    make_lod("Resolution_1", 1, parent=visuals)

    cmds.select(root, replace=True)
    mlod = MLOD.read_file(export_selected("a3ob_nested_scope.p3d"))
    check(len(mlod.lods) == 2, "LODs deeper than one group down, got %d" % len(mlod.lods))


def test_selecting_a_mesh_still_resolves_upward():
    """The existing behaviour: pick the mesh, get its LOD — not every LOD in the scene."""
    new_scene()
    root = cmds.createNode("transform", name="Own_Helmet")
    lod = make_lod("Resolution_0", 0, parent=root)
    make_lod("Resolution_1", 1, parent=root)

    shape = cmds.listRelatives(lod, shapes=True, fullPath=True)[0]
    cmds.select(shape, replace=True)
    mlod = MLOD.read_file(export_selected("a3ob_upward_scope.p3d"))
    check(len(mlod.lods) == 1, "only the LOD the mesh belongs to, got %d" % len(mlod.lods))


def test_a_group_with_no_lods_still_fails():
    """Descending must not turn a genuine mistake into a silent empty export."""
    new_scene()
    group = cmds.createNode("transform", name="geometries")
    cmds.parent(cmds.polyCube(name="just_a_mesh", ch=False)[0], group)

    cmds.select(group, replace=True)
    path = os.path.join(tempfile.gettempdir(), "a3ob_no_lods.p3d")
    if os.path.exists(path):
        os.remove(path)
    try:
        cmds.file(path, force=True, options="selectedOnly=1", type="Arma P3D",
                  exportSelected=True)
    except RuntimeError:
        pass  # the translator raises after the exporter reports the error
    check(not os.path.exists(path),
          "a selection with no LOD in it must not produce a file")


def test_an_empty_lod_still_exports():
    """"Add LOD" makes a marked transform with no mesh; that has to remain exportable."""
    new_scene()
    make_lod("Geometry", 0, with_mesh=False)
    cmds.select("Geometry", replace=True)
    written = export_selected("a3ob_empty_lod.p3d")
    check(os.path.exists(written), "an empty LOD is still a LOD")


def main():
    test_selecting_the_group_exports_the_lods_under_it()
    test_nested_groups_are_followed()
    test_selecting_a_mesh_still_resolves_upward()
    test_a_group_with_no_lods_still_fails()
    test_an_empty_lod_still_exports()
    print("export selection scope: OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
