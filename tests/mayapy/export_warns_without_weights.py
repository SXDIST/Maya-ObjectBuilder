"""Stale a3obBakedWeights must not silence the missing-weights export warning (mayapy).

Bind, stash a stale a3obBakedWeights value directly (Task 6 removed a3obBakeSkin, but the
attribute itself can still linger on a scene saved before that -- e.g. from an older
version of the plugin), delete the rig, export. The bake never fed the export path (Task 5
removed that fallback), so the file comes out with zero bone selections -- but the stale
attribute still holds the OLD data, and `_warn_about_missing_weights` used to treat that as
"weights are fine" and stay silent. That is exactly backwards: the more stale the bake, the
more urgently the warning is needed. This also guards the follow-up where `A.BAKED_WEIGHTS`
itself goes away -- before the fix, the guard above `cmds.ls(type="joint")` would not save
it and the attribute lookup would raise `AttributeError` on every export of a rigged scene.

Run:  mayapy.exe tests/mayapy/export_warns_without_weights.py
"""

import os
import tempfile
from pathlib import Path

import _harness

_harness.bootstrap()

import maya.cmds as cmds
import maya.api.OpenMaya as om


def bone_selections(path):
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    with BinaryReader(str(path)) as reader:
        mlod = MLOD.read(reader)
    return {tagg.name: len(tagg.data.vertex_weights)
            for lod in mlod.lods for tagg in lod.taggs
            if isinstance(tagg.name, str) and not tagg.name.startswith("#")
            and tagg.data is not None and tagg.data.kind == "Selection"}


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.undoInfo(state=True, infinity=True)
    cmds.file(new=True, force=True)

    transform = cmds.polyCylinder(name="staleBake", r=1, h=4, sx=8, sy=4, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")

    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)

    # a3obBakeSkin is gone (Task 6), and store_bake is gone too (Task 7); write the stale
    # attribute directly with cmds, to simulate what a scene saved by an older plugin
    # version can still be carrying.
    cmds.addAttr(transform, longName="a3obBakedWeights", dataType="string")
    cmds.setAttr(transform + ".a3obBakedWeights", "Pelvis:0=1.0;Spine:1=1.0", type="string")
    _harness.check(cmds.getAttr(transform + ".a3obBakedWeights"),
          "the stale data must actually be present on a3obBakedWeights for this "
          "test to mean anything")

    cmds.delete([root, tip])
    _harness.check(not (cmds.ls(type="skinCluster") or []),
          "deleting the joints should have removed the skinCluster")

    # A leftover joint keeps the scene reading as "rigged" for the guard in
    # _warn_about_missing_weights, exactly like a real scene where only ONE mesh's
    # rig got deleted while other joints remain.
    cmds.select(clear=True)
    sentinel = cmds.joint(position=(5, 0, 0), name="Sentinel")

    from a3ob.mayabridge.export.exporter import _warn_about_missing_weights, _lod_sort_key
    selection = om.MSelectionList()
    selection.add(transform)
    dag_path = selection.getDagPath(0)
    unweighted = _warn_about_missing_weights([(_lod_sort_key(dag_path), dag_path)])
    _harness.check(unweighted == [dag_path.partialPathName()],
          "a LOD with a stale bake but no live skinCluster must still be flagged, "
          "got %r" % (unweighted,))

    # And the real export path: the file itself must carry no bone selections, while
    # the stale attribute is still sitting on the transform.
    _harness.check(cmds.getAttr(transform + ".a3obBakedWeights"),
          "the stale attribute must still be present at export time -- that is the "
          "whole point of this regression")

    from a3ob.mayabridge.export.exporter import MayaMeshExport
    path = Path(tempfile.mkdtemp(prefix="stale-bake-")) / "stale_bake.p3d"
    _harness.check(MayaMeshExport().export_mlod(str(path)), "export failed")
    selections = bone_selections(path)
    _harness.check(not selections,
          "export must write no bone selections once the rig and skinCluster are "
          "gone, got %r" % sorted(selections))

    cmds.delete(sentinel)

    print("OK stale a3obBakedWeights no longer silences the missing-weights warning")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
