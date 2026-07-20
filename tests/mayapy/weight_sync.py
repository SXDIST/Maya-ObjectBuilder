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
