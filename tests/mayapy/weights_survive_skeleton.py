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

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = Path(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, str(_REPO / "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


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
    check(MayaMeshExport().export_mlod(str(path)), "export failed for " + label)
    return bone_selections(path)


def main():
    cmds.loadPlugin(os.path.join(str(_REPO), "plug-ins", "MayaObjectBuilder.py"))
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
    check(set(with_rig) == {"Pelvis", "Spine"},
          "the rigged export must carry both bones, got %r" % sorted(with_rig))

    # Bake, then destroy the rig exactly as a user would.
    baked = cmds.a3obBakeSkin()
    baked = baked[0] if isinstance(baked, (list, tuple)) else baked
    check(int(baked) == 1, "expected one LOD baked, got %r" % (baked,))
    check(cmds.getAttr(transform + ".a3obBakedWeights"),
          "baking must write a3obBakedWeights onto the transform")

    cmds.delete([root, tip])
    check(not (cmds.ls(type="skinCluster") or []),
          "deleting the joints should have removed the skinCluster (that is the whole problem)")

    without_rig = export("without_rig")
    check(set(without_rig) == set(with_rig),
          "baked weights must still export every bone: %r vs %r"
          % (sorted(with_rig), sorted(without_rig)))
    for bone, count in with_rig.items():
        check(without_rig[bone] == count,
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
    check(len(unweighted) == 1,
          "exporting a rigged scene with no weights must flag the LOD, got %r" % (unweighted,))

    cmds.delete(joint)

    print("OK weights survive skeleton deletion (%s)"
          % ", ".join("%s=%d" % (b, n) for b, n in sorted(without_rig.items())))
    test_bind_pose_detection()
    test_import_stores_weights_on_mesh()
    return 0


def test_import_stores_weights_on_mesh():
    """A .p3d imported without a skeleton must keep its weights as mesh data."""
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    from a3ob.mayabridge.import_.importer import MayaMeshImport
    from a3ob.mayabridge.skinweights import parse_bake_string

    fixture = (_REPO / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d"
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
        stored_bones.update(name for name, _pairs in parse_bake_string(text))

    check(stored_bones, "import must store weights on the LOD transforms")
    check(stored_bones <= expected,
          "stored bones must all come from the file: %r" % sorted(stored_bones - expected))
    print("OK import stores %d bone selection(s) as mesh data" % len(stored_bones))


def test_bind_pose_detection():
    """Exporting a posed rig bakes the pose into the model, so validation must catch it."""
    from a3ob.mayabridge.posetest import skeleton_is_posed

    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="posed", r=1, h=4, ch=False)[0]
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Root")
    tip = cmds.joint(position=(0, 2, 0), name="Tip")
    cmds.skinCluster(root, tip, mesh, toSelectedBones=True)

    check(skeleton_is_posed() == [], "a freshly bound rig must read as bind pose")

    cmds.setAttr(tip + ".rotateX", 45)
    posed = skeleton_is_posed()
    check(len(posed) == 1 and posed[0].endswith("Tip"),
          "the rotated joint must be reported, got %r" % (posed,))

    cmds.setAttr(tip + ".rotateX", 0)
    check(skeleton_is_posed() == [], "returning to bind pose must clear the warning")
    print("OK bind pose detection (posed rig reported, restored rig clean)")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL weights_survive_skeleton: %s" % error, file=sys.stderr)
        raise
