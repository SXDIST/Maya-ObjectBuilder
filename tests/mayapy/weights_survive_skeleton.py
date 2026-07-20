"""Weights must survive deleting the skeleton (run with mayapy).

Reported from real use: delete the rig, export, and the .p3d comes out with no bone selections
at all — silently. Reproduced exactly: deleting the joints deletes the skinCluster with them,
and the weights only ever lived there.

``a3obBakeSkin`` copies the live weights onto the LOD transform so they outlive the rig, and
export falls back to them when no skinCluster is present. The live skinCluster still wins when
it exists, so baking can never serve stale weights over a rig you are still editing.

Run:  mayapy.exe tests/mayapy/weights_survive_skeleton.py
"""

import os
import sys
import tempfile
from pathlib import Path

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def bone_selections(path):
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    with BinaryReader(str(path)) as reader:
        mlod = MLOD.read(reader)
    return {tagg.name: len(tagg.data.vertex_weights)
            for lod in mlod.lods for tagg in lod.taggs
            if isinstance(tagg.name, str) and not tagg.name.startswith("#")
            and tagg.data is not None and tagg.data.kind == "Selection"}


def export(label):
    from a3ob.mayabridge.export.exporter import MayaMeshExport
    path = Path(tempfile.mkdtemp(prefix="skel-")) / (label + ".p3d")
    _harness.check(MayaMeshExport().export_mlod(str(path)), "export failed for " + label)
    return bone_selections(path)


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.undoInfo(state=True, infinity=True)
    cmds.file(new=True, force=True)

    transform = cmds.polyCylinder(name="rigged", r=1, h=4, sx=8, sy=4, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")

    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)

    with_rig = export("with_rig")
    _harness.check(set(with_rig) == {"Pelvis", "Spine"},
          "the rigged export must carry both bones, got %r" % sorted(with_rig))

    # Bake, then destroy the rig exactly as a user would.
    baked = cmds.a3obBakeSkin()
    baked = baked[0] if isinstance(baked, (list, tuple)) else baked
    _harness.check(int(baked) == 1, "expected one LOD baked, got %r" % (baked,))
    _harness.check(cmds.getAttr(transform + ".a3obBakedWeights"),
          "baking must write a3obBakedWeights onto the transform")

    cmds.delete([root, tip])
    _harness.check(not (cmds.ls(type="skinCluster") or []),
          "deleting the joints should have removed the skinCluster (that is the whole problem)")

    without_rig = export("without_rig")
    _harness.check(set(without_rig) == set(with_rig),
          "baked weights must still export every bone: %r vs %r"
          % (sorted(with_rig), sorted(without_rig)))
    for bone, count in with_rig.items():
        _harness.check(without_rig[bone] == count,
              "bone %s lost vertices: %d with rig, %d without" % (bone, count, without_rig[bone]))

    # And a scene that has a skeleton but no weights at all must not export silently.
    cmds.setAttr(transform + ".a3obBakedWeights", "", type="string")
    cmds.select(clear=True)
    joint = cmds.joint(position=(0, 0, 0), name="Lonely")
    from a3ob.mayabridge.export.exporter import _warn_about_missing_weights, _lod_sort_key
    import maya.api.OpenMaya as om
    selection = om.MSelectionList()
    selection.add(transform)
    dag_path = selection.getDagPath(0)
    unweighted = _warn_about_missing_weights([(_lod_sort_key(dag_path), dag_path)])
    _harness.check(len(unweighted) == 1,
          "exporting a rigged scene with no weights must flag the LOD, got %r" % (unweighted,))

    cmds.delete(joint)

    print("OK weights survive skeleton deletion (%s)"
          % ", ".join("%s=%d" % (b, n) for b, n in sorted(without_rig.items())))
    test_bind_pose_detection()
    test_import_writes_no_bake_on_mesh()
    return 0


def test_import_writes_no_bake_on_mesh():
    """A .p3d imported without a rig must NOT mirror its bone selections onto the
    transform any more (Task 4): the skinCluster import already builds is the only
    store, and import creates no skinCluster of its own, so there is nothing to bake."""
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    from a3ob.mayabridge.import_.importer import MayaMeshImport

    fixture = (Path(_harness.REPO) / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d"
               / "sample_1_character.p3d")
    if not fixture.is_file():
        print("SKIP import weight storage: fixture missing")
        return

    with BinaryReader(str(fixture)) as reader:
        mlod = MLOD.read(reader)

    cmds.file(new=True, force=True)
    MayaMeshImport().import_mlod(mlod, str(fixture))

    baked = cmds.ls("*.a3obBakedWeights", objectsOnly=True) or []
    _harness.check(not baked, "import must not write a3obBakedWeights, got %r" % (baked,))
    print("OK import writes no baked weights onto the LOD transforms")


def test_bind_pose_detection():
    """Exporting a posed rig bakes the pose into the model, so validation must catch it."""
    from a3ob.mayabridge.posetest import skeleton_is_posed

    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="posed", r=1, h=4, ch=False)[0]
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Root")
    tip = cmds.joint(position=(0, 2, 0), name="Tip")
    cmds.skinCluster(root, tip, mesh, toSelectedBones=True)

    _harness.check(skeleton_is_posed() == [], "a freshly bound rig must read as bind pose")

    cmds.setAttr(tip + ".rotateX", 45)
    posed = skeleton_is_posed()
    _harness.check(len(posed) == 1 and posed[0].endswith("Tip"),
          "the rotated joint must be reported, got %r" % (posed,))

    cmds.setAttr(tip + ".rotateX", 0)
    _harness.check(skeleton_is_posed() == [], "returning to bind pose must clear the warning")
    print("OK bind pose detection (posed rig reported, restored rig clean)")
    test_bind_pose_detection_after_middle_influence_removal()


def test_bind_pose_detection_after_middle_influence_removal():
    """Regression: bindPreMatrix is a SPARSE multi indexed by .matrix[] LOGICAL indices,
    which do NOT compact when an influence is removed. Removing a TRAILING influence never
    exposed the bug (the surviving indices stay dense from 0), so this removes a MIDDLE one:
    a 4-joint rig with B and C removed leaves influences=['A', 'D'] but the correct
    bindPreMatrix slots are [0, 3], not [0, 1]. skintransfer.finish_for_dayz() and
    a3obInfluence -ri both remove by name, not by trailing position, so this is the shape a
    real DayZ rig hits on every transfer."""
    from a3ob.mayabridge.posetest import skeleton_is_posed

    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="middleRemoval", r=1, h=6, sx=8, sy=6, ch=False)[0]
    cmds.select(clear=True)
    a = cmds.joint(position=(0, -3, 0), name="A")
    b = cmds.joint(position=(0, -1, 0), name="B")
    c = cmds.joint(position=(0, 1, 0), name="C")
    d = cmds.joint(position=(0, 3, 0), name="D")
    skin = cmds.skinCluster(a, b, c, d, mesh, toSelectedBones=True, maximumInfluences=4)[0]

    cmds.skinCluster(skin, edit=True, removeInfluence=[b, c])
    _harness.check(cmds.skinCluster(skin, query=True, influence=True) == ["A", "D"],
          "expected A and D to survive the removal")

    posed = skeleton_is_posed()
    _harness.check(posed == [],
          "a rig that was never moved must read as bind pose after removing a middle "
          "influence, got %r (mis-indexed bindPreMatrix would report the survivors)" % (posed,))
    print("OK bind pose detection survives a middle-influence removal")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
