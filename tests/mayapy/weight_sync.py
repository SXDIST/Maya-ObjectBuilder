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
